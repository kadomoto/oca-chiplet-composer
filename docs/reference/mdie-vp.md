# mdie-vp

`mdie-vp` runs two OCA chiplets in one SystemC process. Each die is a full `smu_platform` (SMC, SEP and the SMU crossbar) from tt-oca-harness-model, and the two dies' AoUs are connected to each other, replacing each die's stand-in remote peer. It lives on the `feat/mdie-vp` branch of [kadomoto/tt-oca-harness-model](https://github.com/kadomoto/tt-oca-harness-model/tree/feat/mdie-vp).

```text
mdie-vp <smc-ini> <sep-ini> <sim_time_ms> <die0-smc-elf> <die0-sep-elf> <die1-smc-elf> <die1-sep-elf>
```

## Naming

Die 0 keeps smu-vp's names (`dut`, `och_sep_ss1`, `smu_xbar`), so existing inis apply. Die 1 is `dut1`, `och_sep_ss2`, `smu_xbar1`. Every preset loaded for die 0 is cloned to die 1 before the per-die values are applied.

## Ini keys

| Key | Section | Default | Meaning |
|---|---|---|---|
| `mdie.die<k>.smc_global_base` | `[uint]` | `0x4000_0000 + k × 32 MiB` | die k's SMC global window; 16 MiB aligned, at least 32 MiB apart |
| `mdie.die<k>.user_size` | `[uint]` | `0` | size of die k's chiplet logic window; 0 turns it off |
| `mdie.die<k>.user_base` | `[uint]` | `0x7000_0000` | base of the window; at or above `0x7000_0000` |
| `mdie.die<k>.user_model` | `[string]` | | command that implements the logic (see below) |
| `dut.aou.bridge_delay_ns` | `[double]` | `0` | the AoU's per-crossing delay, cloned to both dies |
| `dut.cluster.quantum_insts`, `global_quantum_ns` | `[uint]` | `1000`, `1000` | simulation quantum; the composer uses 5 and 5 for link runs |

`MDIE_VP_VERBOSITY=<n>` in the environment raises the report verbosity, which logs every routing decision.

## Chiplet logic window

With `user_size` > 0, a router between the die's SMU crossbar and its AoU sends the window to the chiplet logic instead of the AoU. `user_model` names a process that `mdie-vp` starts; it receives one line per access on stdin and answers on stdout:

```text
-> R <offset hex> <len hex> <time_ns>            <- OK <value hex> <delay_ns>
-> W <offset hex> <len hex> <value hex> <time_ns> <- OK 0 <delay_ns>
-> Q                                              (end of simulation)
```

`ERR <reason>` answers with a bus error. The process's stderr goes into the simulation log. The composer's [Python runtime](python-model.md) implements this protocol; any program can.

## Limits

- One pair of dies: each die has one AoU, so it has one peer.
- The AoU model is loosely timed: `bridge_delay_ns` is its only timing parameter.
- The logic window has no interrupt line yet.
