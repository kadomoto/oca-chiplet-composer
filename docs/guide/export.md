# Export and rerun

**File → Export simulation bundle** downloads a zip with everything needed to rerun the simulations without the composer.

| Path | Contents |
|---|---|
| `design.json` | the design ([Design file](../reference/design-file.md)) |
| `analytic_report.json` | the analytic model's full output |
| `config/package.json`, `config/<chiplet>.h` | the [generated Harness setup](harness-setup.md) |
| `vp/chiplets/<id>/` | each chiplet's ini and `run.sh` |
| `vp/links/<id>/` | each link's ini, `run.sh` and `fw/` with the firmware sources and generated headers |
| `vp/logic/<id>/` | each chiplet logic run: register map, model, script, generated headers, ini, `run.sh` |

Link and logic `run.sh` scripts are self-contained: they build the firmware next to them and run `mdie-vp`.

```bash
unzip demo-sip-oca.zip -d bundle
source oca-env.sh                # your toolchain
MODEL_ROOT=/path/to/tt-oca-harness-model bash bundle/vp/links/l3/run.sh
```

`MODEL_ROOT` and `MDIE_VP` override where the scripts look for the model and the platform. A logic run's ini names the Python model by absolute path; edit `mdie.die0.user_model` in it if you move the folder.

**File → Save design (JSON)** and **Import design (JSON)…** save and load the design alone.
