# OCA Chiplet Composer (reference GUI)

A web GUI for composing OCA chiplets on a package and simulating the result on the
server. It's a reference prototype built on top of
[tt-oca-harness](https://github.com/tenstorrent/tt-oca-harness) and
[tt-oca-harness-model](https://github.com/tenstorrent/tt-oca-harness-model).

```
Browser (frontend/index.html, vanilla JS + SVG)
  │  place dies (mm), set package tech, draw UCIe links, define traffic, undo/redo
  │  live: POST /api/evaluate        (analytic, ~ms)
  │  sweep: POST /api/sweep          (analytic, one parameter at a time)
  │  run:  POST /api/runs  + SSE /api/runs/{id}/events
  ▼
FastAPI (backend/app.py)
  ├─ engines/analytic.py   DRC (substrate bounds, die gap, UCIe reach, port count,
  │                        per-edge PHY shoreline, non-facing dies), PHY placement on
  │                        die edges, PHY-to-PHY Manhattan channel, link BW/latency,
  │                        latency-routed traffic, M/M/1 load, D2D energy, Murphy yield / cost
  └─ engines/harness_vp.py smu-vp, invoked directly with parallel jobs:
                           • per chiplet: its sw/smu-vp-tests scenario, with
                             dut.aou(_peer).bridge_delay_ns = worst link latency
                           • per link: firmware/oca-latency-probe times 32 AoU accesses
                             with CLINT MTIME → firmware-visible ns/access
                           • once per server: a 0 ns baseline (the on-die share of the cost)
```

What the GUI shows:

* **Canvas.** UCIe PHY blocks sit on the facing die edges. Each link is drawn as a
  Manhattan route between PHYs and coloured by utilisation. Hover a link for its
  details, including the VP measurement.
* **Links / Traffic.** The analytic numbers, plus "VP ns/access" per link and a
  VP-based path estimate per flow, once a Harness VP run exists for the current
  design. VP results are marked stale if the design changes afterwards.
* **Sweep.** Package tech, data rate, modules per link, layout spread or defect
  density against latency, utilisation, D2D power, cost or longest channel, as a
  chart plus a table. Each point shows its DRC status.
* **Harness VP.** Per-chiplet PASS/FAIL and the per-link probe results (measured,
  baseline, and AoU share).

* **Visual design.** The canvas is drawn like an assembly drawing:
  * a solder-mask substrate with dimension lines;
  * silicon dies with a band coloured by chiplet kind;
  * UCIe PHYs as gold bump fields at the package's real bump pitch once zoomed in;
  * copper links, which turn amber or red only at ≥70% or ≥100% utilisation.

  The design summary is a title block. Type is Archivo, with IBM Plex Mono for code
  identifiers only, loaded from Google Fonts with a system-font fallback when offline.

* **Accessibility.** The UI follows the
  [Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines):
  every control is labelled, everything works from the keyboard (arrow keys move the
  selected chiplet; links can be added from the inspector; there are zoom buttons;
  tabs use arrow keys and are kept in the URL as `#tab=`), a live region announces
  DRC and run results, deletions offer Undo, form errors show inline, and light and
  dark themes and phone widths are supported.

On smu-vp, firmware sees about **1.25 ns + 1.5 × bridge_delay_ns per 32-bit access**.
The slope holds from 8 ns to 1 µs, so each access costs about 1.5 AoU traversals.
The GUI reports this as a measurement; it doesn't explain the 1.5.

## Upstream checkouts

`upstream/` is not tracked. The backend expects the Harness model at
`upstream/tt-oca-harness-model`, or wherever `OCA_MODEL_ROOT` points. It must include
the `[double]` INI fix from
[tenstorrent/tt-oca-harness-model#284](https://github.com/tenstorrent/tt-oca-harness-model/pull/284):

```bash
mkdir -p upstream && cd upstream
git clone https://github.com/tenstorrent/tt-oca-harness-model
cd tt-oca-harness-model
git fetch https://github.com/kadomoto/tt-oca-harness-model fix/smu-vp-ini-double
git checkout FETCH_HEAD    # until #284 is merged
```

## Run

```bash
pip install fastapi uvicorn
python3 -m uvicorn app:app --app-dir backend --port 8765
# open http://localhost:8765
```

Harness VP engine: `./start.sh` sources `~/opt/src/oca-deps/oca_env.sh`, which is the
toolchain set up on this machine:

| Dependency | Location | Note |
|---|---|---|
| SystemC 3.0.2 (C++20) | `~/opt/systemc-3.0.2-cxx20` | built from the Accellera tarball |
| CCI 1.0.2 | `~/opt/cci-1.0.2-cxx20` | static, `lib/` |
| Boost 1.74 | `~/opt/boost-1.74-local` | system headers + program_options, plus iostreams unpacked from the Ubuntu .deb (no sudo needed) |
| Whisper `a53d0f3e` | `~/opt/src/oca-deps/whisper` | `-fPIC` libs, using the CI recipe |
| RISC-V GCC | `~/opt/xpack/xpack-riscv-none-elf-gcc-15.2.0-1` | provides RV32 + RV64 multilibs; `~/opt/riscv64` has RV64 only |
| smu-vp | `upstream/tt-oca-harness-model/vp/build_smc/bin/smu-vp` | built with `cmake --build vp/build_smc --target smu-vp` |

```bash
./start.sh       # http://localhost:8765
```

Upstream `sw/smu-vp-tests/run_smu_vp_tests.sh` gives 8/8 PASS with this setup.

### Required patch to tt-oca-harness-model

Submitted upstream as [tenstorrent/tt-oca-harness-model#284](https://github.com/tenstorrent/tt-oca-harness-model/pull/284); see [`upstream-pr/`](upstream-pr/) (commit `d709dc6` on branch `fix/smu-vp-ini-double` in the local clone, plus regression test `smu-aou-delay-test`): smu-vp's
INI parser (`vp/platform/smu/main.cpp`) silently ignores `[double]` sections,
although smc-vp accepts them. Without the patch, `dut.aou.bridge_delay_ns` never
reaches the AoU model. With it, `smu-aou-ext-test` behaves as follows:

* at 8 ns delay it passes;
* at 100 ms delay it cannot finish within the 50 ms window, which shows the
  package-derived latency now reaches the simulation.

This is worth sending upstream.

## Scope / limits

* Physical numbers (reach, pitch, pJ/bit, flight time, cost) are illustrative and
  editable in `backend/catalog.py`. They are not vendor data.
* The AoU model in tt-oca-harness-model is loosely timed: `bridge_delay_ns` is its
  only timing knob, and it has no flit, credit, or QoS timing.
* Only `smu-aou-ext-test` exercises the AoU, so it's the only scenario where
  `bridge_delay_ns` matters. smu-vp runs for a fixed `sim_time_ms` and reports
  PASS/FAIL, not a completion time. Firmware that reads `mtime` around AoU traffic
  would be needed to report latency back to the GUI.
* Each chiplet is simulated in its own `smu-vp` process, and the remote die is the
  `aou_peer_` stub inside `smc_platform`. A true N-die co-simulation needs a multi-die
  SystemC top that cross-wires `aou_core::connect_peer()` between `smu_platform`
  instances. That's the natural upstream contribution.
