# Accept [double] sections in smu-vp INI files

## Problem

`smu-vp`'s INI loader (`vp/platform/smu/main.cpp`, `apply_ini_value()`) handles only
`[bool]`, `[int]`, `[uint]` and `[string]`. Any other section returns without setting a
preset, and nothing reports it.

`smc-vp`'s loader already accepts `[double]` / `[float]`, and `smc_smu_vp.ini` says its
semantics are identical to the smc-vp ini. So an ini that tunes a double CCI parameter
loads cleanly in smu-vp but has no effect. Two examples:

| Parameter | smu-vp default | Effect of the dropped override |
|---|---|---|
| `dut.aou.bridge_delay_ns` | 0.0 | No D2D latency through the AoU LT model |
| `dut.clint.tick_period_ns` | 0.0 (MTIME frozen) | MTIME cannot be enabled from an ini |

We hit this while sweeping AoU `bridge_delay_ns` from package-level link estimates.
Setting it to 100 ms under a 50 ms `sim_time_ms` still let `smu-aou-ext-test` pass.

## Change

- `vp/platform/smu/main.cpp`: add the `[double]` / `[float]` branch, the same as smc-vp
  (2 lines).
- New regression test `sw/smu-vp-tests/smu-aou-delay-test`:
  - The Makefile generates `smc.ini` from `smc_smu_vp.ini` and appends a `[double]`
    section that sets `dut.aou{,_peer}.bridge_delay_ns = 10000` and
    `dut.clint.tick_period_ns = 100`.
  - The SMC firmware activates the AoU, then times 4 write+readback beats to the
    catch-all (`xbar.ext_out` → AoU → peer → `stub_sysmem`) with CLINT MTIME. It requires
    at least 8 × `bridge_delay_ns`.
  - The cluster runs `quantum_insts` instructions per kernel yield, and the CLINT reads
    global time, so annotated delay appears in MTIME only after the hart syncs. Each
    MTIME read therefore follows a spin longer than one batch, and the spin's own cost is
    calibrated out.
  - The SEP half only prints its banner.
- `sw/smu-vp-tests/.gitignore`: ignore the generated `smc.ini`, as is already done for
  `smu-rom-boot-test`.
- `sw/smu-vp-tests/README.md`: add a table row for the new test.

The runner picks up the new directory automatically, so CI needs no workflow change.

## Testing

Run on Ubuntu 22.04 with GCC 11.4, SystemC 3.0.2 and CCI 1.0.2 (C++20), Boost 1.74,
Whisper `a53d0f3e` (`-fPIC`), and xpack `riscv-none-elf-gcc` 15.2.0-1.

| Binary | `smu-aou-delay-test` output |
|---|---|
| without fix | `MTIME delta 0 ticks … = 0 ns (min 80000 ns)` → **FAIL** |
| with fix | `MTIME delta 1610 ticks (spin 400) = 121000 ns (min 80000 ns), 15125 ns/hop` → **PASS** |

`sw/smu-vp-tests/run_smu_vp_tests.sh` with the fix passes 9/9: the existing 8 plus the
new test.

`vp/platform/smu/run_tests.sh` (ASan / coverage) was not run. The change touches
`sc_main` argument handling only, not an IP model.

## Notes / possible follow-ups (not in this PR)

- An unknown section is still silently ignored. A warning in `apply_ini_value()` would
  have caught this immediately.
- The measured cost is ~15 µs per hop against 10 µs configured. The extra comes from
  fabric/stub `access_delay_ns` and batch quantisation. The test asserts only a lower
  bound.
