# Troubleshooting

**The sidebar says `smu-vp: Not built`.**
The server did not find the binary at `upstream/tt-oca-harness-model/vp/build_smc/bin/smu-vp`. Build it (see [Install](getting-started/install.md#4-build-the-platforms)), or set `OCA_MODEL_ROOT` or `OCA_SMU_VP` in `oca-env.sh`, then restart `./start.sh`.

**`mdie-vp: Not built`, and links run as a single-die probe.**
The model checkout lacks the `feat/mdie-vp` branch, or `mdie-vp` was not built. Build the `mdie-vp` target, or set `OCA_MDIE_VP`.

**The VP run is skipped.**
The design has design rule errors. Fix what **Checks** lists, then run again.

**A firmware build fails.**
The Run log shows the compiler's last lines. Check that the RISC-V toolchain has both RV32 and RV64 multilibs; the xPack build does, many distribution packages only have RV64.

**Changing the link delay changes nothing.**
The model checkout lacks the `[double]` INI fix ([#284](https://github.com/tenstorrent/tt-oca-harness-model/pull/284)); without it, `bridge_delay_ns` is ignored. Also, only `smu-aou-ext-test` among the per-chiplet scenarios crosses the AoU.

**A chiplet logic run times out on `poll`, or ends early.**
The model never set the field, or a hook raised an exception. An exception fails the access, which stops the SMC's simulation. Check the model log under **Chiplet logic → Last run**, or `sim.log` in the run folder: the exception is logged there.

**The fonts look different offline.**
The UI loads Instrument Sans and IBM Plex Mono from Google Fonts, and falls back to the system fonts without a network.
