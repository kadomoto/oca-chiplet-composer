# Sweeps

A sweep re-runs the analytic model with one parameter set to each of several values, and plots one result against it. Open the **Sweep** tab, pick what to vary and what to plot, and press **Run sweep**.

| Vary | Values |
|---|---|
| Package technology | organic, silicon interposer, embedded bridge |
| UCIe data rate, all links | 4, 8, 12, 16, 24, 32 GT/s |
| UCIe modules per link, all links | 1, 2, 3, 4 |
| Layout spread | 0.6 to 2.0 × the spacing between die centres |
| Defect density D0 | 0.05 to 0.5 per cm² |

The plot can show the worst flow latency (loaded or zero-load), the highest link utilisation, die-to-die power, silicon plus package cost, or the longest channel. The table below the chart lists all of them for every value.

A hollow point or a faded bar means that value breaks a design rule; hover it to see the first error. Layout spread is a quick way to find where a layout stops fitting: below 1 dies collide, above 1 they may leave the substrate or exceed the reach.

The sweep runs on the current design. Change the design and the composer marks the sweep as out of date.
