# Harness VP runs

Tick **Harness VP** and press **Run simulation** to run the design on tt-oca-harness-model. The sidebar's **Harness VP** section says whether `smu-vp` and `mdie-vp` are built. Design rule errors skip the VP part of the run.

## Jobs

| Job | Platform | Firmware | PASS when |
|---|---|---|---|
| Per chiplet | `smu-vp` | the chiplet's scenario | both the SMC and the SEP print their PASS banner, and nothing prints FAIL |
| Per link | `mdie-vp` | `firmware/oca-d2d-pingpong` | both dies' SMCs finish the ping-pong |
| Per chiplet with logic | `mdie-vp` | `firmware/oca-regscript` | the register script finishes; a failed `poll` or `expect` fails it |

Jobs run in parallel, four at a time. Firmware is built once per job folder before anything runs.

## Per-chiplet scenarios

Choose a chiplet's scenario in its inspector. They are the tests in the model's `sw/smu-vp-tests`. The scenario runs with `dut.aou.bridge_delay_ns` set to the worst latency of the chiplet's links.

Only `smu-aou-ext-test` sends traffic over the AoU; the inspector marks it **crosses AoU**. The others run on one die, so the injected delay does not change them. A scenario that ships its own `smc.ini` (marked in the results) ignores the composer's ini.

## Link runs

Each link runs its two chiplets on `mdie-vp`, with their AoUs connected, for 20 ms of simulated time. The chiplet earlier in the design is die 0. Both dies boot with the [generated setup](harness-setup.md); die 0 checks a remote write and read-back on die 1, then times 16 round trips. See [Simulate links on the Harness](../tutorials/two-die.md) for how to read them.

Without `mdie-vp`, link runs fall back to a single-die probe against the AoU stub peer, which measures the cost per access firmware sees.

## Results

- **Harness VP** tab: per-chiplet results with notes, and the link table.
- **Chiplet logic** tab: each logic run's reads, model log and access trace.
- **Run** tab: the streamed log, including each die's UART output.
- On disk: `runs/<run id>/vp/`, one folder per job with its ini, `run.sh` and `sim.log`.

Results are marked out of date as soon as the design changes.
