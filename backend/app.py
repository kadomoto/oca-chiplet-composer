"""OCA Chiplet Composer — reference server.

    uvicorn app:app --app-dir backend --port 8765
"""
from __future__ import annotations

import asyncio
import io
import tempfile
import json
import threading
import time
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import catalog
from engines import analytic, harness_vp

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
RUNS.mkdir(exist_ok=True)

app = FastAPI(title="OCA Chiplet Composer", version="0.1.0")


# --------------------------------------------------------------------------- schema
class Chiplet(BaseModel):
    id: str
    name: str
    kind: str
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float
    ucie_ports: int = 4
    power_w: float = 0.0
    scenario: str | None = None


class Link(BaseModel):
    id: str
    a: str
    b: str
    modules: int = 1
    data_rate_gtps: float | None = None
    aou_fixed_ns: float | None = None
    phy_ns: float | None = None


class Flow(BaseModel):
    src: str
    dst: str
    gbs: float


class Package(BaseModel):
    tech: str = "ucie-s-organic"
    w_mm: float = 40
    h_mm: float = 30


class Design(BaseModel):
    name: str = "untitled"
    package: Package = Field(default_factory=Package)
    chiplets: list[Chiplet] = []
    links: list[Link] = []
    flows: list[Flow] = []
    process: dict = {}
    sim: dict = {}


class RunRequest(BaseModel):
    design: Design
    engines: list[str] = ["analytic"]


# --------------------------------------------------------------------------- jobs
class Job:
    def __init__(self, design: dict, engines: list[str]):
        self.id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.design, self.engines = design, engines
        self.dir = RUNS / self.id
        self.dir.mkdir(parents=True)
        (self.dir / "design.json").write_text(json.dumps(design, indent=2))
        self.state, self.logs, self.result = "queued", [], {}
        self.cancel = False
        self.created = time.time()

    def log(self, msg):
        self.logs.append(f"{time.strftime('%H:%M:%S')} {msg}")

    def to_dict(self, logs=False):
        d = {"id": self.id, "state": self.state, "engines": self.engines,
             "name": self.design.get("name"), "created": self.created, "result": self.result}
        if logs:
            d["logs"] = self.logs
        return d

    def run(self):
        self.state = "running"
        try:
            a = analytic.run(self.design, self.log)
            self.result["analytic"] = a
            if "harness-vp" in self.engines:
                if a["summary"]["errors"]:
                    self.log("[harness-vp] skipped: fix DRC errors first")
                    self.result["harness_vp"] = {"available": None, "jobs": [], "skipped": True}
                else:
                    self.result["harness_vp"] = harness_vp.run(
                        self.design, a, self.dir / "vp", self.log, lambda: self.cancel)
            self.state = "cancelled" if self.cancel else "done"
        except Exception as e:  # noqa: BLE001
            self.log(f"ERROR: {e!r}")
            self.state = "failed"
        (self.dir / "result.json").write_text(json.dumps(self.result, indent=2))
        (self.dir / "run.log").write_text("\n".join(self.logs))


JOBS: dict[str, Job] = {}


# --------------------------------------------------------------------------- API
@app.get("/api/catalog")
def get_catalog():
    return {"chiplets": catalog.CHIPLET_TEMPLATES, "packages": catalog.PACKAGES,
            "link_defaults": catalog.DEFAULT_LINK, "process": catalog.DEFAULT_PROCESS,
            "harness_vp": harness_vp.status()}


@app.post("/api/evaluate")
def evaluate(design: Design):
    """Synchronous analytic evaluation — called live on every edit."""
    return analytic.run(design.model_dump(), log=lambda *_: None)


SWEEPS = {
    "package.tech": {"label": "Package technology", "values": list(catalog.PACKAGES)},
    "links.data_rate_gtps": {"label": "UCIe data rate (GT/s), all links", "values": [4, 8, 12, 16, 24, 32]},
    "links.modules": {"label": "UCIe modules per link, all links", "values": [1, 2, 3, 4]},
    "layout.scale": {"label": "Layout spread (× die-to-die spacing)", "values": [0.6, 0.8, 1.0, 1.25, 1.5, 2.0]},
    "process.defect_density_per_cm2": {"label": "Defect density D0 (/cm²)", "values": [0.05, 0.1, 0.2, 0.3, 0.5]},
}


def _apply(d: dict, param: str, v):
    if param == "package.tech":
        d["package"]["tech"] = v
    elif param.startswith("links."):
        for l in d["links"]:
            l[param.split(".", 1)[1]] = v
    elif param == "layout.scale":
        # spread die centres about the layout's centroid; die sizes unchanged
        cs = d["chiplets"]
        if cs:
            cx = sum(c["x_mm"] + c["w_mm"] / 2 for c in cs) / len(cs)
            cy = sum(c["y_mm"] + c["h_mm"] / 2 for c in cs) / len(cs)
            for c in cs:
                mx, my = c["x_mm"] + c["w_mm"] / 2, c["y_mm"] + c["h_mm"] / 2
                c["x_mm"] = round(cx + (mx - cx) * v - c["w_mm"] / 2, 3)
                c["y_mm"] = round(cy + (my - cy) * v - c["h_mm"] / 2, 3)
    elif param.startswith("process."):
        d.setdefault("process", {})[param.split(".", 1)[1]] = v
    else:
        raise HTTPException(400, f"unknown sweep parameter {param}")


class SweepRequest(BaseModel):
    design: Design
    param: str
    values: list | None = None


@app.get("/api/sweep/params")
def sweep_params():
    return SWEEPS


@app.post("/api/sweep")
def sweep(req: SweepRequest):
    """Re-run the analytic model for each value of one parameter."""
    import copy
    if req.param not in SWEEPS:
        raise HTTPException(400, f"unknown sweep parameter {req.param}")
    base = req.design.model_dump()
    rows = []
    for v in req.values or SWEEPS[req.param]["values"]:
        d = copy.deepcopy(base)
        _apply(d, req.param, v)
        r = analytic.run(d, log=lambda *_: None)
        s = r["summary"]
        lat = [f["loaded_latency_ns"] for f in r["flows"] if f.get("routable")]
        zl = [f["zero_load_latency_ns"] for f in r["flows"] if f.get("routable")]
        rows.append({
            "value": v,
            "label": catalog.PACKAGES[v]["label"] if req.param == "package.tech" else str(v),
            "errors": s["errors"], "warnings": s["warnings"],
            "first_error": next((i["message"] for i in r["issues"] if i["severity"] == "error"), None),
            "worst_zero_load_ns": round(max(zl), 2) if zl else None,
            "worst_loaded_ns": round(max(lat), 2) if lat else None,
            "max_link_util": s["max_link_utilization"],
            "d2d_power_w": s["d2d_power_w"],
            "total_cost_usd": round(s["silicon_cost_usd"] + s["package_cost_usd"], 2),
            "max_channel_mm": max((l["channel_mm"] for l in r["links"]), default=None),
            "unroutable_flows": sum(not f.get("routable") for f in r["flows"]),
        })
    return {"param": req.param, "label": SWEEPS[req.param]["label"], "rows": rows}


@app.post("/api/config")
def harness_config(design: Design):
    """Generated Harness setup: address map, inbound filters, AoU roles, headers."""
    from engines import config_gen
    d = design.model_dump()
    pkg = config_gen.package_config(d)
    pkg["chiplet_headers"] = {r["chiplet"]: config_gen.chiplet_header(pkg, r["chiplet"])
                              for r in pkg["address_map"] if r["fits"]}
    return pkg


@app.post("/api/runs")
def create_run(req: RunRequest):
    unknown = set(req.engines) - {"analytic", "harness-vp"}
    if unknown:
        raise HTTPException(400, f"unknown engines {unknown}")
    job = Job(req.design.model_dump(), req.engines)
    JOBS[job.id] = job
    threading.Thread(target=job.run, daemon=True).start()
    return job.to_dict()


@app.get("/api/runs")
def list_runs():
    return sorted((j.to_dict() for j in JOBS.values()), key=lambda d: -d["created"])


@app.get("/api/runs/{rid}")
def get_run(rid: str):
    if rid not in JOBS:
        raise HTTPException(404)
    return JOBS[rid].to_dict(logs=True)


@app.post("/api/runs/{rid}/cancel")
def cancel_run(rid: str):
    if rid not in JOBS:
        raise HTTPException(404)
    JOBS[rid].cancel = True
    return {"ok": True}


@app.get("/api/runs/{rid}/events")
async def run_events(rid: str):
    if rid not in JOBS:
        raise HTTPException(404)
    job = JOBS[rid]

    async def gen():
        sent = 0
        while True:
            while sent < len(job.logs):
                yield f"event: log\ndata: {json.dumps(job.logs[sent])}\n\n"
                sent += 1
            if job.state in ("done", "failed", "cancelled"):
                yield f"event: end\ndata: {json.dumps(job.to_dict())}\n\n"
                return
            await asyncio.sleep(0.3)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/export")
def export(design: Design):
    """Zip: design.json, analytic report, per-chiplet smu-vp inis + run.sh."""
    d = design.model_dump()
    a = analytic.run(d, log=lambda *_: None)
    buf = io.BytesIO()
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        p = harness_vp.plan(d, a, Path(tmp))
        z.writestr("design.json", json.dumps(d, indent=2))
        z.writestr("analytic_report.json", json.dumps(a, indent=2))
        for j in p["chiplets"] + p["links"]:
            sub = f"chiplets/{j['chiplet']}" if j["kind"] == "chiplet" else f"links/{j['link']}"
            for f in ("smc_smu_vp.ini", "run.sh"):
                z.write(Path(j["dir"]) / f, f"vp/{sub}/{f}")
            fw = Path(j["dir"]) / "fw"
            if fw.is_dir():   # generated two-die firmware sources + headers for this link
                for f in sorted(fw.iterdir()):
                    if f.is_file() and f.suffix in (".h", ".c", ".mk") or f.name == "Makefile":
                        z.write(f, f"vp/{sub}/fw/{f.name}")
        from engines import config_gen
        cfg = p["config"]
        z.writestr("config/package.json", json.dumps(cfg, indent=2))
        for r in cfg["address_map"]:
            if r["fits"]:
                z.writestr(f"config/{r['chiplet']}.h", config_gen.chiplet_header(cfg, r["chiplet"]))
    buf.seek(0)
    fname = f"{d['name'] or 'design'}-oca.zip".replace(" ", "_")
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


FRONT = ROOT / "frontend"
app.mount("/static", StaticFiles(directory=FRONT), name="static")


@app.get("/")
def index():
    return FileResponse(FRONT / "index.html")
