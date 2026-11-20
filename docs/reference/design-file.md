# Design file

**File → Save design (JSON)** writes the design as one JSON object, and **Import design (JSON)…** reads it back. The browser also keeps the current design in local storage.

```json
{
  "name": "demo-sip",
  "package": {"tech": "ucie-s-organic", "w_mm": 44, "h_mm": 32},
  "chiplets": [
    {"id": "io0", "name": "IO0", "kind": "io", "x_mm": 4, "y_mm": 9, "w_mm": 6, "h_mm": 12,
     "ucie_ports": 4, "power_w": 15, "scenario": "smu-aou-ext-test"}
  ],
  "links": [{"id": "l0", "a": "io0", "b": "c0", "modules": 1}],
  "flows": [{"src": "c0", "dst": "m0", "gbs": 24}],
  "process": {},
  "sim": {"sim_time_ms": 50, "parallel": 4}
}
```

| Key | Meaning |
|---|---|
| `package.tech` | `ucie-s-organic`, `ucie-a-interposer` or `ucie-a-bridge` |
| `chiplets[]` | `kind` is `io`, `compute`, `memory` or `harness`; positions and sizes in mm; `scenario` is the per-chiplet VP test |
| `chiplets[].logic` | optional: `{"enabled": true, "regmap": {…}, "model": "…", "script": "…"}`; see [Register maps](register-map.md) |
| `links[]` | `a`, `b` are chiplet ids; optional `data_rate_gtps`, `aou_fixed_ns`, `phy_ns` override the defaults |
| `flows[]` | `src`, `dst` chiplet ids, `gbs` in GB/s |
| `process` | optional `defect_density_per_cm2`, `wafer_cost_usd` |
| `sim` | `sim_time_ms` for per-chiplet runs, `parallel` jobs at a time |
