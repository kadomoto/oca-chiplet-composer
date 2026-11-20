"""Harness VP engine: drives tt-oca-harness-model's smu-vp.

Two kinds of jobs per run:

  * Chiplet jobs: one per chiplet. The chiplet's functional scenario (a
    sw/smu-vp-tests test) runs on smu-vp with `dut.aou(_peer).bridge_delay_ns` set to
    the worst package-derived latency among that chiplet's links. PASS requires both
    firmware halves to print their PASS banner and no line to print FAIL (same rule as
    run_smu_vp_tests.sh).
  * Link jobs: one per UCIe link.
      - With mdie-vp (two dies, AoUs cross-connected): the link's two chiplets run as
        two real dies, and firmware/oca-d2d-pingpong times SMC-to-SMC round trips over
        the link with CLINT MTIME. A 5 ns quantum keeps the link latency visible
        (it still under-reads delays of a few ns).
      - Otherwise: firmware/oca-latency-probe runs on smu-vp against the AoU stub peer
        and reports the cost per access seen by firmware.
    Either way, a run with zero delay is made once per server process; that baseline
    is the on-die part of the cost.

smu-vp is invoked directly (not through run_smu_vp_tests.sh), so the GUI gets the
VP's UART output and the jobs can run in parallel. Firmware is built once per
scenario, before any job starts.

Limitation: chiplet jobs still run one die against the AoU stub peer, and mdie-vp
connects exactly one pair of dies (one AoU per die).

Needs tt-oca-harness-model with the [double] INI fix
(tenstorrent/tt-oca-harness-model#284). Without it, smu-vp silently drops the
injected delays.
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MODEL_ROOT = Path(os.environ.get(
    "OCA_MODEL_ROOT", ROOT / "upstream" / "tt-oca-harness-model")).resolve()
SMU_VP = Path(os.environ.get("OCA_SMU_VP", MODEL_ROOT / "vp" / "build_smc" / "bin" / "smu-vp"))
TEST_DIR = MODEL_ROOT / "sw" / "smu-vp-tests"
BASE_SMC_INI = MODEL_ROOT / "vp" / "platform" / "smu" / "config" / "smc_smu_vp.ini"
SEP_INI = MODEL_ROOT / "vp" / "platform" / "smu" / "config" / "sep_smu_config.ini"
PROBE_DIR = ROOT / "firmware" / "oca-latency-probe"
PROBE_TICK_NS = 10.0
PROBE_SIM_MS = 5
MDIE_VP = Path(os.environ.get("OCA_MDIE_VP", MODEL_ROOT / "vp" / "build_smc" / "bin" / "mdie-vp"))
D2D_DIR = ROOT / "firmware" / "oca-d2d-pingpong"
D2D_SIM_MS = 20
D2D_QUANTUM = {"dut.cluster.quantum_insts": 5, "global_quantum_ns": 5}   # finer = closer to the injected delay, slower
D2D_TICK_NS = 1.0

_build_lock = threading.Lock()
_built: set[str] = set()
_baseline: dict[str, dict] = {}


# --------------------------------------------------------------------------- discovery
def scenarios() -> list[str]:
    if not TEST_DIR.is_dir():
        return []
    return sorted(p.name for p in TEST_DIR.iterdir() if p.is_dir() and p.name.startswith("smu-"))


def _uses_aou(scen: str) -> bool:
    for f in (TEST_DIR / scen).glob("*.c"):
        t = f.read_text(errors="ignore")
        if "SMC_AOU_BASE" in t or "AOU_INIT" in t:
            return True
    return False


def _own_ini(scen: str) -> bool:
    """Tests that ship (or generate) their own smc.ini override the GUI's ini."""
    mk = TEST_DIR / scen / "Makefile"
    return mk.is_file() and re.search(r"^smc\.ini\s*:", mk.read_text(), re.M) is not None


def status() -> dict:
    sc = scenarios()
    return {
        "model_root": str(MODEL_ROOT),
        "model_found": MODEL_ROOT.is_dir(),
        "smu_vp": str(SMU_VP),
        "smu_vp_found": SMU_VP.is_file() and os.access(SMU_VP, os.X_OK),
        "scenarios": sc,
        "aou_scenarios": [s for s in sc if _uses_aou(s)],
        "own_ini_scenarios": [s for s in sc if _own_ini(s)],
        "probe_found": (PROBE_DIR / "smc_main.c").is_file(),
        "mdie_vp": str(MDIE_VP),
        "mdie_vp_found": _mdie_ok(),
        "toolchain_prefix": os.environ.get("RISCV_PREFIX", ""),
    }


def _mdie_ok() -> bool:
    return MDIE_VP.is_file() and os.access(MDIE_VP, os.X_OK) and (D2D_DIR / "smc_main.c").is_file()


# --------------------------------------------------------------------------- ini
def _ini(delay_ns: float, header: str, tick_ns: float | None = None, uints: dict | None = None) -> str:
    base = BASE_SMC_INI.read_text() if BASE_SMC_INI.is_file() else ""
    s = (base.rstrip() + "\n\n"
         "# ---- injected by OCA Chiplet Composer -----------------------------\n"
         f"# {header}\n"
         "[double]\n"
         f"dut.aou.bridge_delay_ns      : {delay_ns}\n"
         f"dut.aou_peer.bridge_delay_ns : {delay_ns}\n")
    if tick_ns is not None:
        s += f"dut.clint.tick_period_ns     : {tick_ns}\n"
    if uints:
        s += "[uint]\n" + "".join(f"{k} : {v}\n" for k, v in uints.items())
    return s


# --------------------------------------------------------------------------- plan
def plan(design: dict, analytic: dict, workdir: Path) -> dict:
    """Write inis and run.sh for every job; return {'chiplets': [...], 'links': [...]}."""
    sim_ms = design.get("sim", {}).get("sim_time_ms", 50)
    names = {c["id"]: c["name"] for c in design["chiplets"]}
    by_chip: dict[str, float] = {}
    for l in analytic["links"]:
        for c in (l["a"], l["b"]):
            by_chip[c] = max(by_chip.get(c, 0.0), l["aou_bridge_delay_ns"])

    chip_jobs = []
    for c in design["chiplets"]:
        scen = c.get("scenario") or "smu-aou-ext-test"
        d = workdir / "chiplets" / c["id"]
        d.mkdir(parents=True, exist_ok=True)
        delay = round(by_chip.get(c["id"], 0.0), 3)
        ini = d / "smc_smu_vp.ini"
        ini.write_text(_ini(delay, f"chiplet {c['name']} ({c['kind']}), "
                                   f"{c['w_mm']}x{c['h_mm']} mm, scenario {scen}"))
        tdir = TEST_DIR / scen
        own = _own_ini(scen)
        chip_jobs.append({
            "kind": "chiplet", "chiplet": c["id"], "name": c["name"], "scenario": scen,
            "bridge_delay_ns": delay, "ini": str(tdir / "smc.ini") if own else str(ini),
            "ini_overridden": own, "fw_dir": str(tdir), "dir": str(d), "sim_ms": sim_ms,
            "uses_aou": _uses_aou(scen)})

    d2d = _mdie_ok()
    link_jobs = []
    for l in analytic["links"]:
        d = workdir / "links" / l["id"]
        d.mkdir(parents=True, exist_ok=True)
        ini = d / "smc_smu_vp.ini"
        hdr = (f"link {names.get(l['a'])} (die0) <-> {names.get(l['b'])} (die1), "
               f"channel {l['channel_mm']} mm")
        ini.write_text(_ini(l["aou_bridge_delay_ns"], hdr, D2D_TICK_NS if d2d else PROBE_TICK_NS, D2D_QUANTUM if d2d else None))
        link_jobs.append({
            "kind": "link", "mode": "d2d" if d2d else "probe", "link": l["id"],
            "name": f"{names.get(l['a'])}↔{names.get(l['b'])}",
            "dies": [names.get(l["a"]), names.get(l["b"])],
            "bridge_delay_ns": l["aou_bridge_delay_ns"], "ini": str(ini),
            "fw_dir": str(D2D_DIR if d2d else PROBE_DIR), "dir": str(d),
            "sim_ms": D2D_SIM_MS if d2d else PROBE_SIM_MS})

    for j in chip_jobs + link_jobs:
        Path(j["dir"], "run.sh").write_text(
            "#!/usr/bin/env bash\n# Rebuild firmware with `make` in fw_dir first.\nset -e\n"
            f"cd {shlex.quote(j['fw_dir'])}\n" + shlex.join(_cmd(j)) + "\n")
    return {"chiplets": chip_jobs, "links": link_jobs}


def _elves(fw_dir: Path):
    smc = sorted(p for p in fw_dir.iterdir() if p.is_file() and re.fullmatch(r"(smu|oca)_\w+_smc", p.name))
    sep = sorted(p for p in fw_dir.iterdir() if p.is_file() and re.fullmatch(r"(smu|oca)_\w+_sep", p.name))
    return (smc[0] if smc else None), (sep[0] if sep else None)


def _cmd(j) -> list[str]:
    fw = Path(j["fw_dir"])
    if j.get("mode") == "d2d":
        smc0, smc1, sep = (str(fw / f) for f in ("oca_d2d_smc0", "oca_d2d_smc1", "oca_d2d_sep"))
        return [str(MDIE_VP), j["ini"], str(SEP_INI), str(j["sim_ms"]), smc0, sep, smc1, sep]
    smc, sep = _elves(fw) if fw.is_dir() else (None, None)
    smc_arg = str(smc) if smc else "none"
    sep_arg = str(sep) if sep else str(fw / "<sep-elf>")
    return [str(SMU_VP), j["ini"], smc_arg, str(SEP_INI), sep_arg, str(j["sim_ms"])]


# --------------------------------------------------------------------------- execution
def _build(fw_dir: Path, log) -> bool:
    key = str(fw_dir)
    with _build_lock:
        if key in _built:
            return True
        env = {**os.environ, "MODEL_ROOT": str(MODEL_ROOT)}
        args = ["make", "-C", str(fw_dir), "-s"]
        if os.environ.get("RISCV_PREFIX"):
            args.append(f"RISCV_PREFIX={os.environ['RISCV_PREFIX']}")
        p = subprocess.run(args, env=env, capture_output=True, text=True)
        if p.returncode != 0:
            log(f"[harness-vp] firmware build FAILED in {fw_dir}:")
            for line in (p.stdout + p.stderr).splitlines()[-15:]:
                log(f"[harness-vp]   {line}")
            return False
        _built.add(key)
        log(f"[harness-vp] built firmware: {fw_dir.name}")
        return True


# Lines worth streaming to the GUI; everything still goes to sim.log.
_KEEP = re.compile(r"^(smu-vp:|mdie-vp:|===|.*\bPASS:|.*\bFAIL:|OCA_PROBE|OCA_D2D|SMC->|SEP->|AOU|ERROR)")
_UART_BEGIN = re.compile(r"^---- (die(\d) )?SMC UART0 output")
_UART_END = re.compile(r"^---- end (die\d )?SMC UART0")


def _exec(j, log, cancelled, quiet=False) -> dict:
    if cancelled():
        return {**j, "result": "CANCELLED"}
    cmd = _cmd(j)
    if j.get("mode") != "d2d" and cmd[2] == "none" and not j.get("ini_overridden"):
        return {**j, "result": "FAIL (no SMC ELF after build)"}
    logf = Path(j["dir"]) / "sim.log"
    with subprocess.Popen(cmd, cwd=j["fw_dir"], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True) as p, logf.open("w") as fh:
        in_uart, tag = False, ""
        for line in p.stdout:
            fh.write(line)
            t = line.rstrip()
            if (m := _UART_BEGIN.match(t)):
                in_uart, tag = True, (f"die{m.group(2)} uart0 │ " if m.group(2) else "uart0 │ ")
                continue
            if _UART_END.match(t):
                in_uart = False
                continue
            if not quiet and t and (in_uart or _KEEP.match(t)):
                log(f"[{j['name']}] {tag if in_uart else ''}{t}")
            if cancelled():
                p.kill()
        rc = p.wait()
    text = logf.read_text()
    if j.get("mode") == "d2d":
        # Two SEPs share one console and interleave, so judge on the two SMC banners.
        smc_ok = all(re.search(rf"PASS: .*die{k} \(SMC side\)", text) for k in (0, 1))
        sep_ok = True
    else:
        smc_ok = re.search(r"PASS: .*SMC side", text) is not None
        sep_ok = re.search(r"PASS: .*SEP side", text) is not None
    fail = re.search(r"FAIL:.*", text)
    if cancelled():
        res = "CANCELLED"
    elif smc_ok and sep_ok and not fail:
        res = "PASS"
    elif fail:
        res = "FAIL (" + fail.group(0)[5:].strip()[:80] + ")"
    else:
        res = f"FAIL (no PASS banner within {j['sim_ms']} ms" + (f", rc={rc})" if rc else ")")
    out = {**j, "result": res, "returncode": rc, "log": str(logf), "cmd": shlex.join(cmd)}
    m = re.search(r"OCA_PROBE hops=(\d+) ticks=(\d+) spin=(\d+)", text)
    if m:
        hops, ticks, spin = map(int, m.groups())
        out["probe"] = {"mode": "probe", "hops": hops, "ticks": ticks, "spin": spin,
                        "ns_per_access": round(max(ticks - spin, 0) * PROBE_TICK_NS / hops, 2)}
    m = re.search(r"OCA_D2D rounds=(\d+) ticks=(\d+)", text)
    if m:
        rounds, ticks = map(int, m.groups())
        rtt = ticks * D2D_TICK_NS / rounds
        # ns_per_access: one-way message latency (half a round trip), for the shared columns
        out["probe"] = {"mode": "d2d", "rounds": rounds, "ticks": ticks,
                        "rtt_ns": round(rtt, 2), "ns_per_access": round(rtt / 2, 2)}
    return out


def _get_baseline(mode: str, log, cancelled) -> dict | None:
    if mode not in _baseline:
        d = ROOT / "runs" / f"_baseline_{mode}"
        d.mkdir(parents=True, exist_ok=True)
        ini = d / "smc_smu_vp.ini"
        d2d = mode == "d2d"
        ini.write_text(_ini(0.0, "baseline: bridge_delay_ns = 0", D2D_TICK_NS if d2d else PROBE_TICK_NS, D2D_QUANTUM if d2d else None))
        r = _exec({"kind": "baseline", "mode": mode, "name": "baseline", "ini": str(ini),
                   "fw_dir": str(D2D_DIR if d2d else PROBE_DIR), "dir": str(d),
                   "sim_ms": D2D_SIM_MS if d2d else PROBE_SIM_MS}, log, cancelled, quiet=True)
        if "probe" in r and r["result"] == "PASS":
            _baseline[mode] = r["probe"]
            what = (f"round trip {r['probe']['rtt_ns']} ns between two dies" if d2d
                    else f"{r['probe']['ns_per_access']} ns/access")
            log(f"[harness-vp] baseline at bridge_delay 0: {what}")
        else:
            log(f"[harness-vp] baseline run failed: {r['result']}")
            return None
    return _baseline[mode]


def run(design: dict, analytic: dict, workdir: Path, log=print, cancelled=lambda: False) -> dict:
    st = status()
    p = plan(design, analytic, workdir)
    if not st["smu_vp_found"]:
        log(f"[harness-vp] smu-vp not found at {st['smu_vp']}")
        log("[harness-vp] build it: cmake -S vp -B vp/build_smc && cmake --build vp/build_smc "
            "--target smu-vp (needs SystemC 3.0.2, CCI 1.0.2, Whisper, RISC-V GCC). "
            "Or set OCA_SMU_VP / OCA_MODEL_ROOT.")
        log("[harness-vp] wrote an ini and run.sh per job so they can be run by hand.")
        nr = lambda js: [{**j, "result": "NOT RUN"} for j in js]
        return {"available": False, "jobs": nr(p["chiplets"]), "links": nr(p["links"])}

    fw_dirs = {Path(j["fw_dir"]) for j in p["chiplets"] + p["links"]}
    built = {d: _build(d, log) for d in sorted(fw_dirs)}
    mode = p["links"][0]["mode"] if p["links"] else None
    if mode == "d2d":
        log(f"[harness-vp] links: two-die co-simulation on {MDIE_VP.name} (AoU pair cross-connected)")
    base = _get_baseline(mode, log, cancelled) if mode and built.get(Path(p["links"][0]["fw_dir"])) else None

    def one(j):
        if not built.get(Path(j["fw_dir"])):
            return {**j, "result": "FAIL (firmware build)"}
        r = _exec(j, log, cancelled, quiet=(j["kind"] == "link"))
        if j["kind"] == "link" and "probe" in r:
            pr = r["probe"]
            if base:
                pr["baseline_ns"] = base["ns_per_access"]
                pr["aou_ns_per_access"] = round(pr["ns_per_access"] - base["ns_per_access"], 2)
                if j["bridge_delay_ns"] > 0:
                    pr["aou_crossings_per_access"] = round(
                        pr["aou_ns_per_access"] / j["bridge_delay_ns"], 2)
            if pr["mode"] == "d2d":
                log(f"[harness-vp] link {j['name']}: injected {j['bridge_delay_ns']} ns → "
                    f"SMC↔SMC round trip {pr['rtt_ns']} ns, one way {pr['ns_per_access']} ns ({r['result']})")
            else:
                log(f"[harness-vp] link {j['name']}: injected {j['bridge_delay_ns']} ns → "
                    f"firmware sees {pr['ns_per_access']} ns/access ({r['result']})")
        elif j["kind"] == "chiplet":
            log(f"[harness-vp] {j['name']} / {j['scenario']}: {r['result']}")
        return r

    workers = max(1, int(design.get("sim", {}).get("parallel", 4)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        chips = list(ex.map(one, p["chiplets"]))
        links = list(ex.map(one, p["links"]))
    return {"available": True, "jobs": chips, "links": links, "baseline": base, "link_mode": mode}
