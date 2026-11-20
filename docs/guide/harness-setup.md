# Generated Harness setup

Before two chiplets can talk over the AoU, firmware on each one has to get three things right. They are easy to get wrong by hand, and the composer derives them from the design. The **Harness config** tab shows the result.

## Address map

Each chiplet gets a 32 MiB slot in the global address map, in design order from `0x4000_0000`:

| Range in the slot | What it is |
|---|---|
| base … base + 16 MiB | the chiplet's SMC global window, which other chiplets address |
| base + 16 … base + 32 MiB | the SMC's outbound remap windows (M-mode, then Xvisor) |

The SEP aperture starts at `0x5000_0000`, so eight chiplets fit. A ninth is a design rule error. Firmware programs the SMC fabric's `GLOBAL_BASE` CSR (`0xC001_0000`) to its slot at boot; `mdie-vp` sets the matching crossbar aperture from `mdie.die<k>.smc_global_base`.

!!! note "Why 32 MiB"
    An SMC treats addresses just above its own window as its remap windows. A peer placed there would never be reached, so each chiplet claims both. `mdie-vp` rejects windows that are not 16 MiB aligned or are closer than 32 MiB.

## Inbound filters

The SMC inbound filter blocks all traffic from outside the die by default. Each chiplet opens one entry: its mailbox page, read and write, non-secure, at 4 KiB granularity (`FILTER_CONFIG = 0x01000113`), for the peers it links to.

## AoU bring-up

On each link, the chiplet earlier in the design activates its AoU, which also brings the peer's AoU up. The other waits until its AoU reports ENABLED before it sends anything, so the activating chiplet's filter is already open.

## Where it goes

| Output | Used by |
|---|---|
| `oca_config_die0.h`, `oca_config_die1.h` per link | `firmware/oca-d2d-pingpong`, built per link run |
| `mdie.die<k>.smc_global_base` in the link's ini | `mdie-vp` |
| `config/package.json` and `config/<chiplet>.h` in the export bundle | your own firmware |

A per-chiplet header lists its window, each link peer with the peer's base and whether this chiplet activates the link, and its filter entries:

```c
#define OCA_CHIPLET_NAME     "Compute0"
#define OCA_SELF_GLOBAL_BASE 0x42000000ULL
#define OCA_LINK_COUNT       3u
#define OCA_LINK0_PEER_NAME   "IO0"
#define OCA_LINK0_PEER_BASE   0x40000000ULL
#define OCA_LINK0_INITIATOR   0u
/* ... */
#define OCA_IB_FILTER0_START 0x42063000ULL
#define OCA_IB_FILTER0_END   0x42063FFFULL
#define OCA_IB_FILTER0_CFG   0x01000113u   /* allows IO0, Compute1, Mem0 */
```

`POST /api/config` with the design returns the same data; see [HTTP API](../reference/http-api.md).
