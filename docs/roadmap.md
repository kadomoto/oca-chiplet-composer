# Limitations and roadmap

The composer is a prototype for early exploration, and whether this is the right shape for such a tool is still open. This page lists what it does not do yet.

## Limitations

- **One pair of dies per simulation.** Each die in the model has one AoU, so `mdie-vp` connects exactly two dies. Each link is simulated on its own; a package with several links per die is not simulated in one run.
- **Loosely timed AoU.** `bridge_delay_ns` is the AoU model's only timing parameter; there is no flit, credit or QoS timing. Delays of a few ns read low at the 5 ns quantum.
- **Per-chiplet scenarios still use the stub peer.** Only link runs connect real dies.
- **No interrupt from chiplet logic.** Register scripts poll.
- **No free-form firmware yet.** Firmware is the upstream scenarios, the link firmware and register scripts.
- **Illustrative physics.** Reach, pitch, energy and cost are defaults to edit, not vendor data.
- **No authentication.** Keep the server on `127.0.0.1` or a network you trust.

## Possible next steps

- Several AoUs per die, so a whole package runs in one simulation.
- An interrupt line from the chiplet logic window to the SMC's PLIC.
- A firmware editor with server-side builds, per chiplet and core.
- Separate consoles per die, and a timeline of the traffic between dies.
- Chiplet logic as RTL through Verilator behind the same window.
- Physical reference collateral, such as PHY models and layouts on an open PDK.
