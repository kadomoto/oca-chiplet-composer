/* SPDX-License-Identifier: Apache-2.0 */
/*
 * OCA Chiplet Composer latency probe (SMC side).
 *
 * Activates the AoU and times NBEATS write+readback pairs to the SMU catch-all
 * (xbar.ext_out -> AoU -> peer -> stub_sysmem) with CLINT MTIME.  Each access
 * crosses the AoU once.  The cluster steps quantum_insts instructions per
 * kernel yield and the CLINT reads global time, so settle() spins past a batch
 * boundary before each MTIME read and the spin cost is calibrated out.
 *
 * Prints one machine-readable line the server parses:
 *   OCA_PROBE hops=<n> ticks=<raw> spin=<spin>
 * The server knows dut.clint.tick_period_ns (it wrote the ini).
 */
#include "smc_common.h"

extern int printf(const char *fmt, ...);

#define AOU_INIT                0x08u
#define AOU_INIT_ACTIVATE_START (1u << 0)
#define AOU_INIT_STATE_ENABLED  (1u << 2)
#define EXT_ADDR                0xA0003000ULL
#define NBEATS                  16u
#define SETTLE_ITERS            4000u
#define REG32(a)                (*(volatile uint32_t *)(uintptr_t)(a))

static void settle(void)
{
    for (volatile uint32_t i = 0; i < SETTLE_ITERS; ++i) {
    }
}

static uint64_t mtime(void)
{
    uint32_t hi, lo;
    do {
        hi = REG_READ(SMC_CLINT_BASE + CLINT_MTIME_HI);
        lo = REG_READ(SMC_CLINT_BASE + CLINT_MTIME_LO);
    } while (hi != REG_READ(SMC_CLINT_BASE + CLINT_MTIME_HI));
    return ((uint64_t)hi << 32) | lo;
}

int main(void)
{
    REG_WRITE(SMC_AOU_BASE + AOU_INIT, AOU_INIT_ACTIVATE_START);
    if ((REG_READ(SMC_AOU_BASE + AOU_INIT) & AOU_INIT_STATE_ENABLED) == 0) {
        printf("FAIL: AOU not ENABLED\n");
        return 1;
    }

    settle();
    const uint64_t c0 = mtime();
    settle();
    const uint64_t spin = mtime() - c0;

    settle();
    const uint64_t t0 = mtime();
    for (uint32_t i = 0; i < NBEATS; ++i) {
        REG32(EXT_ADDR + 4u * i) = 0x0CA00000u + i;
        if (REG32(EXT_ADDR + 4u * i) != 0x0CA00000u + i) {
            printf("FAIL: beat %u readback mismatch\n", i);
            return 1;
        }
    }
    settle();
    const uint64_t raw = mtime() - t0;

    printf("OCA_PROBE hops=%u ticks=%u spin=%u\n", 2u * NBEATS, (uint32_t)raw, (uint32_t)spin);
    printf("PASS: OCA latency probe (SMC side)\n");
    return 0;
}
