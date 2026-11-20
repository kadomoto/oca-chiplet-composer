/* SPDX-License-Identifier: Apache-2.0 */
/*
 * OCA Chiplet Composer die-to-die ping-pong (SMC side), for mdie-vp.
 *
 * Each die first programs its SMC fabric GLOBAL_BASE CSR to its slot in the
 * package address map (0x4000_0000 + DIE * 64 MiB), so traffic addressed to the
 * other die's window leaves through the SMU crossbar's ext_out, crosses the
 * AoU pair, and lands in the other die's SMC scratchpad.
 *
 * The SMC inbound filter blocks by default, so each die also opens one entry
 * for its mailbox page to non-secure traffic from the peer.
 *
 *   die 0: set base, open filter, activate the AoU (this also brings die 1's
 *          AoU up), wait for READY, check a remote write + read-back on die 1,
 *          then time ROUNDS ping-pongs with CLINT MTIME.
 *   die 1: set base, open filter, wait until its AoU is ENABLED (so die 0's
 *          filter is already open), send READY, then answer each PING.
 *
 * Machine-readable result (die 0):
 *   OCA_D2D rounds=<n> ticks=<mtime ticks for all rounds>
 */
#include "smc_common.h"

extern int printf(const char *fmt, ...);

#ifndef DIE
#error "build with -DDIE=0 or 1 (see smc_die0.c / smc_die1.c)"
#endif
#define PEER                (1 - DIE)

#define FABRIC_GLOBAL_BASE  0xC0010000ULL            /* GCSR_GLOBAL_BASE */
#define IB_FILTER(n)        (0xC0015000ULL + 0x20ULL * (n))
#define FILTER_RW_NS_4K     0x01000113u              /* read, write, enable, allow_ns, 4 KiB */
#define GLOBAL(k)           (0x40000000ULL + (uint64_t)(k) * 0x04000000ULL)  /* 64 MiB per die, as mdie-vp */
#define SPM_OFF             0x00060000ULL            /* scratchpad in the SMC map */
#define CELLS               0x3100ULL
#define LOCAL(off)          (0xC0000000ULL + SPM_OFF + CELLS + (off))
#define REMOTE(off)         (GLOBAL(PEER) + SPM_OFF + CELLS + (off))
#define C_READY             0x0u
#define C_PING              0x4u
#define C_PONG              0x8u
#define C_PROBE             0x10u

#define AOU_INIT                0x08u
#define AOU_INIT_ACTIVATE_START (1u << 0)
#define AOU_INIT_STATE_ENABLED  (1u << 2)

#define MAGIC_READY         0xD1E00001u
#define TOKEN(i)            (0x0CA00000u | (i))
#define ROUNDS              16u
#define SPIN_LIMIT          2000000u
#define REG32(a)            (*(volatile uint32_t *)(uintptr_t)(a))

static uint64_t mtime(void)
{
    uint32_t hi, lo;
    do {
        hi = REG_READ(SMC_CLINT_BASE + CLINT_MTIME_HI);
        lo = REG_READ(SMC_CLINT_BASE + CLINT_MTIME_LO);
    } while (hi != REG_READ(SMC_CLINT_BASE + CLINT_MTIME_HI));
    return ((uint64_t)hi << 32) | lo;
}

static void open_inbound_window(void)
{
    const uint64_t lo = (GLOBAL(DIE) + SPM_OFF + CELLS) & ~0xFFFULL;
    REG_WRITE(IB_FILTER(0) + 0x08, (uint32_t)lo);           /* START_ADDR */
    REG_WRITE(IB_FILTER(0) + 0x0C, (uint32_t)(lo >> 32));
    REG_WRITE(IB_FILTER(0) + 0x10, (uint32_t)(lo + 0xFFF)); /* END_ADDR */
    REG_WRITE(IB_FILTER(0) + 0x14, (uint32_t)((lo + 0xFFF) >> 32));
    REG_WRITE(IB_FILTER(0) + 0x00, FILTER_RW_NS_4K);        /* FILTER_CONFIG */
}

static int wait_for(uint64_t addr, uint32_t want, const char *what)
{
    for (uint32_t n = 0; REG32(addr) != want; ++n) {
        if (n > SPIN_LIMIT) {
            printf("FAIL: die%u timed out waiting for %s (got 0x%08x)\n", DIE, what, REG32(addr));
            return 0;
        }
    }
    return 1;
}

int main(void)
{
    REG_WRITE(FABRIC_GLOBAL_BASE, (uint32_t)GLOBAL(DIE));
    printf("\n=== OCA d2d ping-pong, die%u (SMC side) ===\n", DIE);
    printf("die%u: SMC global window 0x%08x\n", DIE, REG_READ(FABRIC_GLOBAL_BASE));

    open_inbound_window();

#if DIE == 1
    for (uint32_t n = 0; (REG_READ(SMC_AOU_BASE + AOU_INIT) & AOU_INIT_STATE_ENABLED) == 0; ++n) {
        if (n > SPIN_LIMIT) { printf("FAIL: die1 AoU never came up\n"); return 1; }
    }
    printf("die1: AoU link up\n");
    REG32(REMOTE(C_READY)) = MAGIC_READY;
    for (uint32_t i = 1; i <= ROUNDS; ++i) {
        if (!wait_for(LOCAL(C_PING), TOKEN(i), "PING")) return 1;
        REG32(REMOTE(C_PONG)) = TOKEN(i);
    }
    printf("die1: answered %u pings from die0\n", ROUNDS);
#else
    REG_WRITE(SMC_AOU_BASE + AOU_INIT, AOU_INIT_ACTIVATE_START);
    if ((REG_READ(SMC_AOU_BASE + AOU_INIT) & AOU_INIT_STATE_ENABLED) == 0) {
        printf("FAIL: die0 AoU not ENABLED\n");
        return 1;
    }
    if (!wait_for(LOCAL(C_READY), MAGIC_READY, "READY from die1")) return 1;
    printf("die0: die1 is up\n");

    REG32(REMOTE(C_PROBE)) = 0x5A5AA5A5u;
    const uint32_t back = REG32(REMOTE(C_PROBE));
    if (back != 0x5A5AA5A5u) {
        printf("FAIL: die0 remote read-back 0x%08x\n", back);
        return 1;
    }
    printf("die0: remote write + read-back on die1 OK\n");

    const uint64_t t0 = mtime();
    for (uint32_t i = 1; i <= ROUNDS; ++i) {
        REG32(REMOTE(C_PING)) = TOKEN(i);
        if (!wait_for(LOCAL(C_PONG), TOKEN(i), "PONG")) return 1;
    }
    const uint64_t ticks = mtime() - t0;
    printf("OCA_D2D rounds=%u ticks=%u\n", ROUNDS, (uint32_t)ticks);
#endif
    printf("PASS: OCA d2d ping-pong die%u (SMC side)\n", DIE);
    return 0;
}
