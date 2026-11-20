/* SPDX-License-Identifier: Apache-2.0 */
/*
 * OCA Chiplet Composer die-to-die ping-pong (SMC side), for mdie-vp.
 *
 * All package-specific setup comes from the generated header (oca_config_die<N>.h,
 * written by backend/engines/config_gen.py from the design):
 *   OCA_SELF_GLOBAL_BASE / OCA_PEER_GLOBAL_BASE  this die's and the peer's SMC
 *       global windows in the package address map;
 *   OCA_IB_FILTER<n>_*  inbound filter entries this die opens (the SMC inbound
 *       filter blocks by default);
 *   OCA_AOU_INITIATOR  1: activate the AoU (this also brings the peer up);
 *       0: wait until the AoU is ENABLED, so the initiator's filter is open.
 *
 *   initiator (die 0 of the run): program base, open filter, activate the AoU,
 *       wait for READY, check a remote write + read-back, then time ROUNDS
 *       ping-pongs with CLINT MTIME.
 *   responder (die 1): program base, open filter, wait for ENABLED, send READY,
 *       then answer each PING with a PONG.
 *
 * Machine-readable result (initiator):
 *   OCA_D2D rounds=<n> ticks=<mtime ticks for all rounds>
 */
#include "smc_common.h"

extern int printf(const char *fmt, ...);

#ifndef OCA_SELF_GLOBAL_BASE
#error "include a generated oca_config_die<N>.h first (see smc_die0.c / smc_die1.c)"
#endif

#define FABRIC_GLOBAL_BASE  0xC0010000ULL            /* GCSR_GLOBAL_BASE */
#define IB_FILTER(n)        (0xC0015000ULL + 0x20ULL * (n))
#define LOCAL(off)          (0xC0000000ULL + OCA_MAILBOX_OFF + (off))
#define REMOTE(off)         (OCA_PEER_GLOBAL_BASE + OCA_MAILBOX_OFF + (off))
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

static void set_filter(unsigned n, uint64_t lo, uint64_t hi, uint32_t cfg)
{
    REG_WRITE(IB_FILTER(n) + 0x08, (uint32_t)lo);           /* START_ADDR */
    REG_WRITE(IB_FILTER(n) + 0x0C, (uint32_t)(lo >> 32));
    REG_WRITE(IB_FILTER(n) + 0x10, (uint32_t)hi);           /* END_ADDR */
    REG_WRITE(IB_FILTER(n) + 0x14, (uint32_t)(hi >> 32));
    REG_WRITE(IB_FILTER(n) + 0x00, cfg);                    /* FILTER_CONFIG last: enables the entry */
}

static void open_inbound_filters(void)
{
#if OCA_IB_FILTER_COUNT > 0
    set_filter(0, OCA_IB_FILTER0_START, OCA_IB_FILTER0_END, OCA_IB_FILTER0_CFG);
#endif
#if OCA_IB_FILTER_COUNT > 1
    set_filter(1, OCA_IB_FILTER1_START, OCA_IB_FILTER1_END, OCA_IB_FILTER1_CFG);
#endif
}

static int wait_for(uint64_t addr, uint32_t want, const char *what)
{
    for (uint32_t n = 0; REG32(addr) != want; ++n) {
        if (n > SPIN_LIMIT) {
            printf("FAIL: die%u timed out waiting for %s (got 0x%08x)\n", OCA_DIE_INDEX, what, REG32(addr));
            return 0;
        }
    }
    return 1;
}

int main(void)
{
    REG_WRITE(FABRIC_GLOBAL_BASE, (uint32_t)OCA_SELF_GLOBAL_BASE);
    printf("\n=== OCA d2d ping-pong, die%u = %s (SMC side) ===\n", OCA_DIE_INDEX, OCA_CHIPLET_NAME);
    printf("die%u: SMC global window 0x%08x, peer %s at 0x%08x\n", OCA_DIE_INDEX,
           REG_READ(FABRIC_GLOBAL_BASE), OCA_PEER_NAME, (uint32_t)OCA_PEER_GLOBAL_BASE);
    open_inbound_filters();

#if OCA_AOU_INITIATOR
    REG_WRITE(SMC_AOU_BASE + AOU_INIT, AOU_INIT_ACTIVATE_START);
    if ((REG_READ(SMC_AOU_BASE + AOU_INIT) & AOU_INIT_STATE_ENABLED) == 0) {
        printf("FAIL: die%u AoU not ENABLED\n", OCA_DIE_INDEX);
        return 1;
    }
    if (!wait_for(LOCAL(C_READY), MAGIC_READY, "READY from the peer")) return 1;
    printf("die%u: %s is up\n", OCA_DIE_INDEX, OCA_PEER_NAME);

    REG32(REMOTE(C_PROBE)) = 0x5A5AA5A5u;
    const uint32_t back = REG32(REMOTE(C_PROBE));
    if (back != 0x5A5AA5A5u) {
        printf("FAIL: die%u remote read-back 0x%08x\n", OCA_DIE_INDEX, back);
        return 1;
    }
    printf("die%u: remote write + read-back on %s OK\n", OCA_DIE_INDEX, OCA_PEER_NAME);

    const uint64_t t0 = mtime();
    for (uint32_t i = 1; i <= ROUNDS; ++i) {
        REG32(REMOTE(C_PING)) = TOKEN(i);
        if (!wait_for(LOCAL(C_PONG), TOKEN(i), "PONG")) return 1;
    }
    const uint64_t ticks = mtime() - t0;
    printf("OCA_D2D rounds=%u ticks=%u\n", ROUNDS, (uint32_t)ticks);
#else
    for (uint32_t n = 0; (REG_READ(SMC_AOU_BASE + AOU_INIT) & AOU_INIT_STATE_ENABLED) == 0; ++n) {
        if (n > SPIN_LIMIT) { printf("FAIL: die%u AoU never came up\n", OCA_DIE_INDEX); return 1; }
    }
    printf("die%u: AoU link up\n", OCA_DIE_INDEX);
    REG32(REMOTE(C_READY)) = MAGIC_READY;
    for (uint32_t i = 1; i <= ROUNDS; ++i) {
        if (!wait_for(LOCAL(C_PING), TOKEN(i), "PING")) return 1;
        REG32(REMOTE(C_PONG)) = TOKEN(i);
    }
    printf("die%u: answered %u pings from %s\n", OCA_DIE_INDEX, ROUNDS, OCA_PEER_NAME);
#endif
    printf("PASS: OCA d2d ping-pong die%u (SMC side)\n", OCA_DIE_INDEX);
    return 0;
}
