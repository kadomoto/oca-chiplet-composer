# Analytic model

The analytic model (`backend/engines/analytic.py`) runs on every edit. All constants are illustrative and live in `backend/catalog.py` and at the top of `analytic.py`.

## Links

| Quantity | Formula |
|---|---|
| Channel | Manhattan distance between the two PHYs + 2 × escape (1.0 mm standard, 0.3 mm advanced) |
| Lanes | modules × lanes per module |
| Bandwidth per direction | lanes × data rate ÷ 8, in GB/s |
| Latency | AoU fixed (6 ns) + PHY (2 ns) + channel × flight time per mm |
| Shoreline per die | ⌈bumps ÷ rows⌉ × bump pitch, with bumps = lanes × 2 × 1.2 and 4 rows (standard) or 10 (advanced) |
| PHY depth | 0.8 mm standard, 0.6 mm advanced |

## Traffic

| Quantity | Formula |
|---|---|
| Path | lowest total latency; each intermediate chiplet adds 5 ns |
| Utilisation | the larger direction's load ÷ bandwidth per direction |
| Loaded latency | Σ link latency ÷ (1 − utilisation), utilisation capped at 0.99, plus intermediate hops |
| Die-to-die power | Σ flow bandwidth × 8 × hops × energy per bit |

## Cost

| Quantity | Formula |
|---|---|
| Dies per wafer | π (d/2)² ÷ A − π d ÷ √(2A), for wafer diameter d (300 mm) and die area A |
| Yield | Murphy: ((1 − e^(−A·D0)) ÷ (A·D0))², with A in cm² |
| Die cost | wafer cost ÷ (dies per wafer × yield) |
| Package cost | substrate area × cost per mm² × 10 (substrate and assembly as one lump) |

Defaults: D0 = 0.1 per cm², wafer cost $17,000.
