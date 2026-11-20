# Simulate links on the Harness

In this tutorial you run the example design on the Harness virtual platform and read what firmware measured. Every chiplet runs SMC and SEP firmware, and every UCIe link runs its two chiplets as two connected dies.

When you finish, you know where each result comes from: which firmware ran, with which address map, and how the package's link latency shows up in a round trip between two chiplets.

## Before you start

You need the Harness virtual platform: see [Install](../getting-started/install.md#add-the-harness-virtual-platform). The sidebar should read `smu-vp: Ready` and `mdie-vp: Ready (two dies)`.

Load the example design with **File → Load example design**.

## 1. Run

Tick **Harness VP** in the header and press **Run simulation**. The **Run** tab streams the server log. For the example design the run takes about a minute; most of it is building firmware and starting a simulator per job.

The run makes three kinds of jobs:

| Job | Platform | Firmware |
|---|---|---|
| One per chiplet | `smu-vp` | the chiplet's scenario, chosen in its inspector (an upstream `sw/smu-vp-tests` test) |
| One per link | `mdie-vp` | `firmware/oca-d2d-pingpong` on both dies, built against the generated setup |
| One per chiplet with logic | `mdie-vp` | `firmware/oca-regscript` (see [Model a chiplet's own logic](chiplet-logic.md)) |

## 2. Read the link results

When the run ends, the **Harness VP** tab opens. Its link table has one row per link:

| Column | Meaning |
|---|---|
| Analytic latency | the link latency the analytic model computed from the package |
| Injected | what the composer passed to the AoU model as `bridge_delay_ns` |
| Round trip | firmware on die 0 writes to die 1's mailbox and waits for the reply, 16 times, timed with CLINT MTIME |
| One way | half the round trip |
| Link per crossing | one way minus the baseline: what the package adds each time a message crosses |

For the example design, each link injects about 8 ns. A round trip takes about 77 ns, of which about 66 ns is the baseline: the same run with no link delay, which covers the on-die paths and polling.

!!! note "Why the link share reads low"
    The simulation advances in quanta. Link runs use a 5 ns quantum so that a few nanoseconds are visible at all, but small delays still read low: an 8 ns delay adds about 11 ns per round trip rather than 16. Larger delays track closely.

## 3. See what firmware booted with

Open **Harness config**. Before the two dies of a link can talk, each one's firmware:

1. programs its SMC global window from the address map,
2. opens an SMC inbound filter entry for its peer, because the filter blocks everything by default,
3. brings up the AoU in order: one die activates it, the other waits until it is enabled.

The composer generated all three from the design. Each link run built its firmware against two headers (`oca_config_die0.h`, `oca_config_die1.h`), shown per chiplet at the bottom of the tab. See [Generated Harness setup](../guide/harness-setup.md).

## 4. Change the package and run again

Move a compute die further from the IO die, or set a link's **AoU fixed (ns)** to `50` in its inspector. The Harness VP results are marked out of date as soon as the design changes. Run again: the injected latency and the round trip grow by the same amount, twice per round trip.

## Next

- [Harness VP runs](../guide/harness-vp.md) covers the per-chiplet scenarios and what PASS means.
- [mdie-vp](../reference/mdie-vp.md) documents the two-die platform itself.
