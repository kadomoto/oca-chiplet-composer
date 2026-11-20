# Links and traffic

## Links

A link joins two chiplets with one or more UCIe modules. Create one with **Link tool** (<kbd>L</kbd>) and two clicks, or with **Add link** in a chiplet's inspector.

The composer places a PHY on the edge of each die that faces the other and packs several PHYs on one edge side by side. The channel is the Manhattan distance between the two PHYs plus escape routing at each end. Select a link to edit it:

| Field | Default | Effect |
|---|---|---|
| Modules | 1 | lanes = modules × lanes per module; bandwidth scales with it |
| Data rate (GT/s) | 16 | bandwidth per direction = lanes × rate ÷ 8 |
| AoU fixed (ns) | 6 | added to the link latency |
| PHY (ns) | 2 | added to the link latency |

The link latency is AoU fixed + PHY + flight time over the channel. This is the value the Harness VP runs inject as `bridge_delay_ns`. The **Links** tab lists every link's gap, channel, lanes, bandwidth, load, utilisation, latency and shoreline.

On the canvas a link turns amber at 70 % utilisation and red at 100 % or when it exceeds the reach.

## Traffic

The **Traffic** tab holds flows: a source chiplet, a destination and a bandwidth in GB/s. Each flow is routed on the lowest-latency path, where passing through an intermediate chiplet adds 5 ns.

| Column | Meaning |
|---|---|
| Path | the chiplets the flow passes through |
| Zero-load | the sum of link latencies (and intermediate hops) on the path |
| Loaded | each link's latency inflated by 1 ÷ (1 − utilisation), an M/M/1 estimate |
| VP estimate | the sum of the Harness VP's one-way times on the path, after a VP run |

A flow that no link path can carry shows as unroutable. Die-to-die power is the traffic times the hops it crosses times the technology's energy per bit.
