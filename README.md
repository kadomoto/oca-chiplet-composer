# OCA Chiplet Composer

Lay out chiplets on a package in your browser, then check the result with two kinds of models: a fast analytic model that answers as you edit, and the [Open Chiplet Atlas Harness](https://github.com/tenstorrent/tt-oca-harness) virtual platform running real firmware. The composer also generates the Harness setup the firmware boots with: the package address map, the inbound filter entries and the AoU bring-up order.

![Demo: dragging a die updates the checks; switching to a silicon interposer shows UCIe-A reach errors; a new die is added and linked; a Harness VP run simulates each link as two real dies; the Harness config tab shows the generated address map, AoU bring-up order and per-chiplet headers; a sweep compares package technologies](docs/demo.gif)

> [!NOTE]
> This is an independent research prototype built on Tenstorrent's open-source OCA Harness repositories. It is not an official Tenstorrent project. The physical numbers it uses (reach, bump pitch, energy, cost) are illustrative defaults, not vendor data.

## Why

Choosing chiplet sizes, a package technology and die-to-die links is a physical decision, but its effects show up in system behaviour: link latency, bandwidth, power and cost, and what firmware actually sees. The composer keeps both in one loop:

1. **Analytic model, on every edit.** Placement rules, UCIe reach, where each PHY sits on the die edge and how much shoreline it takes, link bandwidth and latency, traffic routing and load, die-to-die power, yield and cost.
2. **Harness VP, on demand.** The same design runs on the virtual platform from [tt-oca-harness-model](https://github.com/tenstorrent/tt-oca-harness-model). Each chiplet runs SMC and SEP firmware. Each UCIe link runs its two chiplets as two real dies whose AXI-over-UCIe (AoU) bridges are connected to each other, with the latency derived from the package, and firmware on one die exchanges messages with the other.

## Features

- Drag-and-drop editor with dies drawn to scale on a package that looks like the real thing: an organic substrate, a silicon interposer for 2.5D, or embedded bridges under each link
- UCIe PHYs placed on the facing die edges, and links routed between them, shown as an X-ray view through the dies
- Live design rule checks: substrate bounds, die spacing, UCIe reach, PHY shoreline per die edge, UCIe module count, and dies that don't face each other
- Traffic flows routed on the lowest-latency path, with per-link utilisation and loaded latency
- Sweeps over package technology, data rate, modules per link, layout spread or defect density
- Harness VP runs: a firmware scenario per chiplet, and a two-die co-simulation per link that measures the round trip between the two chiplets' SMCs
- Generated Harness setup: a package address map (each chiplet's SMC global window), SMC inbound filter entries and the AoU bring-up order per link, as JSON and C headers that the link firmware boots with
- Chiplet logic: give a chiplet a register map and a Python model of what it does beyond the Harness, then drive it from firmware with a short register script
- Export of a bundle with the design, the analytic report, the generated setup, and a self-contained `run.sh` for every job
- Undo and redo, full keyboard operation, and light and dark themes

Design decisions for the UI are recorded in [`.impeccable.md`](.impeccable.md).

## Getting started

### Prerequisites

- Python 3.10 or later
- A modern browser
- For the Harness VP only: Linux, and the toolchain listed under [Add the Harness VP](#add-the-harness-vp-optional)

### Quick start (analytic model only)

```bash
git clone https://github.com/kadomoto/oca-chiplet-composer
cd oca-chiplet-composer
pip install -r backend/requirements.txt
./start.sh
```

Then open http://127.0.0.1:8765. Choose **File → Load example design** to start from a five-chiplet package.

Everything except the **Harness VP** checkbox works without further setup. The sidebar shows `smu-vp: Not built` until you complete the next section.

### Add the Harness VP (optional)

The composer drives `smu-vp`, the SMC + SEP virtual platform in tt-oca-harness-model.

1. **Get the model with the composer's two changes.** Both are on the `feat/mdie-vp` branch of [kadomoto/tt-oca-harness-model](https://github.com/kadomoto/tt-oca-harness-model/tree/feat/mdie-vp):

   - the `[double]` INI fix ([tenstorrent/tt-oca-harness-model#284](https://github.com/tenstorrent/tt-oca-harness-model/pull/284)): without it, smu-vp ignores the injected link delay;
   - `mdie-vp`, the two-die platform with the dies' AoUs connected to each other.

   ```bash
   mkdir -p upstream && cd upstream
   git clone https://github.com/tenstorrent/tt-oca-harness-model
   cd tt-oca-harness-model
   git fetch https://github.com/kadomoto/tt-oca-harness-model feat/mdie-vp
   git checkout FETCH_HEAD
   git submodule update --init --recursive
   ```

   On a checkout without `mdie-vp`, the composer still works and runs each link as a single-die latency probe against the AoU stub peer.

2. **Install the toolchain** that tt-oca-harness-model's CI uses:

   | Dependency | Version | Note |
   |---|---|---|
   | SystemC | 3.0.2 | built with `-std=c++20` |
   | CCI | 1.0.2 | |
   | Boost | 1.74 or later | needs `iostreams` and `program_options` |
   | OpenSSL | 3.x | |
   | [Whisper](https://github.com/tenstorrent/whisper) | commit `a53d0f3e` | built with `-fPIC` for smu-vp |
   | RISC-V GCC | xPack 15.2.0-1 | must provide both RV32 (SEP) and RV64 (SMC) multilibs |

   The model's [README](https://github.com/tenstorrent/tt-oca-harness-model#building-the-sep-vp) has the build steps.

3. **Point the composer at it.** Copy the template and fill in your paths:

   ```bash
   cp oca-env.example.sh oca-env.sh
   ```

4. **Build smu-vp:**

   ```bash
   source oca-env.sh
   cd upstream/tt-oca-harness-model
   cmake -S vp -B vp/build_smc -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=20 -DSMC_CXX_STANDARD=20
   cmake --build vp/build_smc --target smu-vp mdie-vp -j
   ```

5. **Check it.** Restart `./start.sh`. The sidebar should show `smu-vp: Ready`, `mdie-vp: Ready (two dies)` and nine scenarios. As an extra check, `sw/smu-vp-tests/run_smu_vp_tests.sh` in the model repository should report all tests passing.

> [!TIP]
> If the model lives elsewhere, set `OCA_MODEL_ROOT` and `OCA_SMU_VP` in `oca-env.sh`. `./start.sh` also reads the file named by `OCA_ENV`.

## Using the composer

![The composer with five chiplets on a UCIe-S organic package, the design summary above the canvas, and Harness VP results below](docs-screenshot.png)

1. **Set up the package.** In the header, choose the package technology and the substrate size in millimetres. The canvas draws each one the way it is built:

   | Technology | Typical use | Drawn as |
   |---|---|---|
   | UCIe-S, organic | 2D multi-die packages, dies a few mm apart | dies on a build-up laminate substrate with pin 1 and fiducials |
   | UCIe-A, silicon interposer | 2.5D, e.g. compute dies with HBM stacks | dies packed on a silicon interposer that sits on the substrate |
   | UCIe-A, embedded bridge | 2.5D without a full interposer | a silicon bridge under each link, spanning the gap between the dies |

   ![Two compute dies, two HBM stacks and an IO die on a silicon interposer](docs-interposer.png)

2. **Place chiplets.** Drag a chiplet from the left palette onto the substrate, or press it to add one. Move a chiplet by dragging it or with the arrow keys, and resize it from its bottom-right corner. You can also type its position, size, power and number of UCIe modules in the inspector on the right.
3. **Connect them.** Press **Link tool** (or <kbd>L</kbd>) and click two chiplets, or use **Add link** in a chiplet's inspector. Each link gets a PHY on the facing edge of both dies. Select a link to set its UCIe modules, data rate and fixed latencies.
4. **Add traffic.** In the **Traffic** tab, add flows between chiplets with a bandwidth in GB/s. Each flow is routed on the lowest-latency path.
5. **Read the results.** The design summary above the canvas updates as you edit. The tabs below hold the details:

   | Tab | Shows |
   |---|---|
   | Checks | Design rule errors and warnings, each with a link to the chiplet or link it concerns |
   | Links | Gap, channel length, lanes, bandwidth, load, utilisation, latency and shoreline per link |
   | Traffic | Each flow's path, zero-load and loaded latency, and the Harness VP estimate |
   | Dies & cost | Area, yield and cost per die, and the package |
   | Harness config | The generated setup: address map, AoU bring-up per link, inbound filter entries and a header per chiplet |
   | Chiplet logic | The register map, Python model and register script of the selected chiplet, the generated C header, and the last run's reads, model log and access trace |
   | Sweep | One parameter varied across values, as a chart and a table |
   | Run | The server log of the last run |
   | Harness VP | Per-chiplet scenario results and per-link latency probes |

6. **Run the Harness VP.** Tick **Harness VP** and press **Run simulation**. Each chiplet runs its scenario, chosen in its inspector. Each link runs its two chiplets together on `mdie-vp`: die 1 comes up and reports to die 0, die 0 checks a remote write and read-back, and the two SMCs exchange 16 ping-pongs over the link. Results come back in about a minute for the example design. They are marked out of date when you change the design afterwards.
7. **Save or export.** Under **File**, save or import the design as JSON, or export a simulation bundle with an ini and `run.sh` for every job so you can rerun them by hand.

### Chiplet logic

A chiplet is more than its Harness. To model what it does, select it and press **Add chiplet logic** in the inspector; it starts from a two-register map. The **Chiplet logic** tab then holds three things:

| Part | What you write | What the composer does with it |
|---|---|---|
| Register map | Registers with an offset, an access type (`rw`, `ro`, `wo`, `w1c`, `fifo_w`, `fifo_r`), a reset value and named fields, plus model parameters | Gives every register its default behaviour, generates the C header firmware uses and a Python skeleton, and checks names, offsets and fields |
| Python model | A `Model(RegisterModel)` class that overrides `update()`, `on_write()` or `on_read()` | Runs it behind the chiplet's logic window (`0x7000_0000` on its own die) through `mdie-vp`'s `py_bridge`; every access carries the simulation time |
| Register script | One step per line: `write REG VALUE\|FIELD`, `read REG`, `poll REG.FIELD`, `expect REG[.FIELD] VALUE`, `wait NS` | Compiles it into a table that `firmware/oca-regscript` runs on the chiplet's SMC |

The window has no interrupt line yet, so scripts poll.

### Keyboard

| Key | Action |
|---|---|
| Arrow keys | Move the selected chiplet by 0.5 mm (2 mm with <kbd>Shift</kbd>) |
| <kbd>L</kbd> | Turn the link tool on or off |
| <kbd>Delete</kbd> | Delete the selection (undo from the notification or with <kbd>Ctrl</kbd>+<kbd>Z</kbd>) |
| <kbd>Ctrl</kbd>+<kbd>Z</kbd>, <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Z</kbd> | Undo, redo |
| <kbd>+</kbd> <kbd>−</kbd> <kbd>0</kbd> | Zoom in, zoom out, fit the substrate |
| <kbd>Esc</kbd> | Leave the link tool or close the File menu |

## How it works

```text
Browser: frontend/index.html (plain JavaScript and SVG)
  │  POST /api/evaluate   analytic model, on every edit
  │  POST /api/sweep      analytic model, one parameter across values
  │  POST /api/runs       analytic + optional Harness VP; progress over SSE
  ▼
FastAPI server: backend/app.py
  ├─ engines/analytic.py     rule checks, PHY placement, link budgets, routing, power, cost
  └─ engines/harness_vp.py   runs smu-vp from tt-oca-harness-model
        ├─ per chiplet: its sw/smu-vp-tests scenario, with dut.aou.bridge_delay_ns
        │               set to the worst latency of its links
        ├─ per link:    mdie-vp runs the link's two chiplets as two dies with their AoUs
        │               connected; firmware/oca-d2d-pingpong times SMC-to-SMC round trips
        │               (without mdie-vp: firmware/oca-latency-probe against the AoU stub)
        └─ once:        the same run at 0 ns, giving the on-die share of the cost
```

The link latency injected into the VP is the AoU fixed latency plus the PHY latency plus the flight time over the routed channel (PHY to PHY, plus escape routing).

On `mdie-vp`, a round trip between the two SMCs takes about **66 ns + 2 × `bridge_delay_ns`**: one crossing each way, plus on-die paths and polling. Link runs use a 5 ns simulation quantum so that the link latency is visible. Even so, delays of a few ns read low (an 8 ns delay adds about 11 ns per round trip instead of 16).

### Generated Harness setup

Before two chiplets can talk over the AoU, firmware has to get three things right. `backend/engines/config_gen.py` derives them from the design:

| Setup | What the composer generates |
|---|---|
| Address map | Each chiplet gets a 32 MiB slot from `0x4000_0000`: its 16 MiB SMC global window, followed by its outbound remap windows. Eight chiplets fit below the SEP aperture at `0x5000_0000`; more is a design rule error. |
| Inbound filters | The SMC inbound filter blocks everything by default. Each chiplet opens one entry for its mailbox page to the peers it links to. |
| AoU bring-up | On each link, the chiplet earlier in the design activates the AoU, which also brings the peer up. The other waits for ENABLED before sending anything, so the activator's filter is already open. |

Each link run gets two generated headers (`fw/oca_config_die0.h`, `fw/oca_config_die1.h`), which `firmware/oca-d2d-pingpong` boots with, and `mdie.die<k>.smc_global_base` keys in its ini for `mdie-vp`. The export bundle adds `config/package.json` and a header per chiplet.

### Project structure

```text
backend/
  app.py                 HTTP API, run jobs, sweeps, bundle export
  catalog.py             chiplet templates, package technologies, defaults
  engines/analytic.py    analytic model
  engines/config_gen.py  generated Harness setup (address map, filters, AoU roles)
  engines/regmap.py      register maps: checks, C header, Python skeleton, register scripts
  engines/harness_vp.py  Harness VP runner
firmware/oca-d2d-pingpong/    two-die link firmware; reads the generated oca_config_die<N>.h
firmware/oca-latency-probe/   single-die fallback probe
firmware/oca-regscript/       runs a generated register script against the chiplet logic
usermodel/runtime.py          Python runtime behind the chiplet logic window
frontend/index.html      the whole web UI
upstream-pr/             the smu-vp INI fix as sent upstream (#284)
oca-env.example.sh       toolchain paths template for the Harness VP
start.sh                 starts the server
```

Run outputs go to `runs/`, which git ignores.

## Limitations

> [!IMPORTANT]
> `mdie-vp` connects one pair of dies, because each die in the model has a single AoU. Each link is simulated as its own pair; a whole package with several links per die isn't simulated in one run yet. The per-chiplet scenarios still run against the AoU stub peer.

- The AoU model is loosely timed. `bridge_delay_ns` is its only timing parameter; there is no flit, credit or QoS timing.
- Of the upstream scenarios, only `smu-aou-ext-test` sends traffic over the AoU. The others run on one die, so the injected delay doesn't affect them. The inspector says which kind each scenario is.
- Physical defaults live in `backend/catalog.py` and are illustrative. Change them to match the technology you are studying.
- The server has no authentication. Keep it on `127.0.0.1` or a network you trust.

## Related

- [tt-oca-harness](https://github.com/tenstorrent/tt-oca-harness): OCA Harness RTL, documentation and register tooling
- [tt-oca-harness-model](https://github.com/tenstorrent/tt-oca-harness-model): SystemC/TLM virtual platforms of the Harness
- [tenstorrent/tt-oca-harness-model#284](https://github.com/tenstorrent/tt-oca-harness-model/pull/284): the smu-vp `[double]` INI fix the composer depends on
