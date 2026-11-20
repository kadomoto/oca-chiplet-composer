# Overview

The OCA Chiplet Composer helps you explore a multi-chiplet package before any physical design exists. You place chiplets on a substrate, connect them with UCIe links and add traffic. The composer then checks the design two ways.

| | Analytic models | Harness virtual platform |
|---|---|---|
| When | On every edit, in milliseconds | When you press **Run simulation**, about a minute |
| What | Design rules, link bandwidth and latency, traffic load, die-to-die power, yield and cost | SMC and SEP firmware on every chiplet; each link as two dies talking over AXI-over-UCIe |
| Where | `backend/engines/analytic.py` | [tt-oca-harness-model](https://github.com/tenstorrent/tt-oca-harness-model) (`smu-vp`, `mdie-vp`) |

The point is to keep the physical choices (die sizes, package technology, link widths) and what the system sees (latency, bandwidth, what firmware measures) in one loop.

## The Harness in one paragraph

Every chiplet in Tenstorrent's Open Chiplet Atlas (OCA) carries the *Harness*: a System Management Controller (SMC, RV64 cores), a Secure Enclave Processor (SEP, an RV32 core with crypto), the SMU interconnect that joins them, and an AXI-over-UCIe bridge (AoU) to other chiplets. tt-oca-harness-model simulates it in SystemC/TLM, and runs real firmware on both cores.

## What the composer adds

- **A package view.** Dies drawn to scale on an organic substrate, a silicon interposer or embedded bridges; a UCIe PHY on the facing edge of both dies of each link.
- **Two dies per link.** `mdie-vp` runs a link's two chiplets in one simulation, with their AoUs connected, and firmware on one die exchanges messages with the other. See [mdie-vp](reference/mdie-vp.md).
- **The setup firmware needs.** Each chiplet's address window, the SMC inbound filter entries and the AoU bring-up order, generated from the design. See [Generated Harness setup](guide/harness-setup.md).
- **Chiplet logic.** What a chiplet does beyond the Harness, as a register map and a Python model, driven by its own firmware. See [Model a chiplet's own logic](tutorials/chiplet-logic.md).

## How it fits together

```text
Browser (frontend/index.html)
  │  edits ─▶ /api/evaluate       analytic models
  │  run   ─▶ /api/runs (+ SSE)   analytic + Harness virtual platform
  ▼
FastAPI server (backend/)
  ├─ analytic model ............ design rules, link budgets, routing, power, cost
  ├─ setup generator ........... address map, filters, AoU bring-up
  ├─ register maps ............. checks, C header, Python skeleton, scripts
  └─ VP runner ................. tt-oca-harness-model
        ├─ per chiplet ........... an upstream test scenario on smu-vp
        ├─ per link .............. mdie-vp: the link's two chiplets as two dies
        └─ per chiplet with logic  mdie-vp: firmware drives the Python model
```
