<p align="center">
  <img src="docs/assets/logo.svg" alt="" width="72">
</p>

<h1 align="center">OCA Chiplet Composer</h1>

<p align="center">
  <strong>Lay out chiplets on a package, and check the design against the OCA Harness.</strong><br>
  Fast analytic models as you edit, and the Harness virtual platform running real firmware on every chiplet.
</p>

<p align="center">
  <a href="https://kadomoto.github.io/oca-chiplet-composer/">Documentation</a> ·
  <a href="https://kadomoto.github.io/oca-chiplet-composer/getting-started/install/">Install</a> ·
  <a href="https://kadomoto.github.io/oca-chiplet-composer/getting-started/first-package/">Your first package</a> ·
  <a href="https://kadomoto.github.io/oca-chiplet-composer/tutorials/two-die/">Simulate links</a> ·
  <a href="https://kadomoto.github.io/oca-chiplet-composer/reference/register-map/">Reference</a>
</p>

![Demo: dragging a die updates the checks; switching to a silicon interposer shows UCIe-A reach errors; a new die is added and linked; a compute chiplet gets its own logic; a Harness VP run simulates each link as two real dies; the generated Harness setup and the chiplet logic results are shown; a sweep compares package technologies](docs/demo.gif)

> [!NOTE]
> An independent research prototype built on Tenstorrent's open-source [OCA Harness](https://github.com/tenstorrent/tt-oca-harness) repositories, not an official Tenstorrent project. Whether this is the right shape for such a tool is still open. The physical numbers are illustrative defaults, not vendor data.

## What it does

- **Package layout.** Dies to scale on an organic substrate, a silicon interposer or embedded bridges, joined by UCIe links with a PHY on the facing edge of each die.
- **Analytic models on every edit.** Design rules, link bandwidth and latency, traffic load, die-to-die power, yield and cost, and one-parameter sweeps.
- **The Harness virtual platform.** SMC and SEP firmware on every chiplet, and each link run as two dies whose AXI-over-UCIe bridges are connected.
- **The setup firmware needs.** The address map, SMC inbound filters and AoU bring-up order, generated from the design.
- **Chiplet logic.** What a chiplet does beyond the Harness, as a register map and a Python model, driven by its own firmware.

## Quick start

```bash
git clone https://github.com/kadomoto/oca-chiplet-composer
cd oca-chiplet-composer
pip install -r backend/requirements.txt
./start.sh
```

Open http://127.0.0.1:8765. The example design loads on first start. The analytic models need only Python; the Harness virtual platform needs Linux, a SystemC toolchain and a build of tt-oca-harness-model, covered in [Install](https://kadomoto.github.io/oca-chiplet-composer/getting-started/install/#add-the-harness-virtual-platform).

## Documentation

The documentation is at **[kadomoto.github.io/oca-chiplet-composer](https://kadomoto.github.io/oca-chiplet-composer/)**. Its source is in [`docs/`](docs/).

- **Start:** [Overview](https://kadomoto.github.io/oca-chiplet-composer/overview/) · [Install](https://kadomoto.github.io/oca-chiplet-composer/getting-started/install/) · [Your first package](https://kadomoto.github.io/oca-chiplet-composer/getting-started/first-package/)
- **Tutorials:** [Simulate links on the Harness](https://kadomoto.github.io/oca-chiplet-composer/tutorials/two-die/) · [Model a chiplet's own logic](https://kadomoto.github.io/oca-chiplet-composer/tutorials/chiplet-logic/)
- **Guides:** [Packages and design rules](https://kadomoto.github.io/oca-chiplet-composer/guide/packages/) · [Links and traffic](https://kadomoto.github.io/oca-chiplet-composer/guide/links-traffic/) · [Sweeps](https://kadomoto.github.io/oca-chiplet-composer/guide/sweeps/) · [Harness VP runs](https://kadomoto.github.io/oca-chiplet-composer/guide/harness-vp/) · [Generated Harness setup](https://kadomoto.github.io/oca-chiplet-composer/guide/harness-setup/) · [Export and rerun](https://kadomoto.github.io/oca-chiplet-composer/guide/export/)
- **Reference:** [Register maps](https://kadomoto.github.io/oca-chiplet-composer/reference/register-map/) · [Register scripts](https://kadomoto.github.io/oca-chiplet-composer/reference/register-script/) · [Python model API](https://kadomoto.github.io/oca-chiplet-composer/reference/python-model/) · [mdie-vp](https://kadomoto.github.io/oca-chiplet-composer/reference/mdie-vp/) · [Analytic model](https://kadomoto.github.io/oca-chiplet-composer/reference/analytic-model/) · [HTTP API](https://kadomoto.github.io/oca-chiplet-composer/reference/http-api/)
- **Help:** [Troubleshooting](https://kadomoto.github.io/oca-chiplet-composer/troubleshooting/) · [Limitations and roadmap](https://kadomoto.github.io/oca-chiplet-composer/roadmap/)

To preview the site locally: `pip install mkdocs==1.6.1 mkdocs-material==9.7.7 && mkdocs serve`.

## Built on

[tt-oca-harness](https://github.com/tenstorrent/tt-oca-harness) and [tt-oca-harness-model](https://github.com/tenstorrent/tt-oca-harness-model) by Tenstorrent. The two-die platform and the chiplet logic window are on the [`feat/mdie-vp`](https://github.com/kadomoto/tt-oca-harness-model/tree/feat/mdie-vp) branch of a fork; the `[double]` INI fix they rely on is [tenstorrent/tt-oca-harness-model#284](https://github.com/tenstorrent/tt-oca-harness-model/pull/284).
