/* SPDX-License-Identifier: Apache-2.0 */
/*
 * Runs a register script against the chiplet's own logic (its window at
 * OCA_LOGIC_BASE, served by a model through mdie-vp's py_bridge).
 * The script is generated from what a person wrote in the composer
 * (backend/engines/regmap.py: parse_script / script_header).
 *
 * Output the composer parses:
 *   OCA_REG <step> <name> 0x<value> t=<mtime>      after each read / poll / expect
 *   FAIL: ...                                      on a poll timeout or a mismatch
 */
#include "smc_common.h"
#include "oca_script.h"

extern int printf(const char *fmt, ...);
#define REG32(a) (*(volatile uint32_t *)(uintptr_t)(a))

static uint32_t mtime_lo(void) { return REG_READ(SMC_CLINT_BASE + CLINT_MTIME_LO); }

int main(void)
{
    printf("\n=== OCA register script on %s (%u steps) ===\n", OCA_LOGIC_NAME, OCA_SCRIPT_LEN);
    for (uint32_t i = 0; i < OCA_SCRIPT_LEN; ++i) {
        const oca_step_t *s = &oca_script[i];
        const uint64_t a = OCA_LOGIC_BASE + s->off;
        uint32_t v = 0;
        switch (s->op) {
        case OP_WRITE:
            REG32(a) = s->value;
            break;
        case OP_READ:
            v = REG32(a);
            printf("OCA_REG %u %s 0x%08x t=%u\n", i, s->name, v, mtime_lo());
            break;
        case OP_POLL: {
            uint32_t n = 0;
            while (((v = REG32(a)) & s->mask) != s->value) {
                if (++n > s->timeout) {
                    printf("FAIL: step %u: %s stayed 0x%08x (waiting for 0x%08x under mask 0x%08x)\n",
                           i, s->name, v, s->value, s->mask);
                    return 1;
                }
            }
            printf("OCA_REG %u %s 0x%08x t=%u\n", i, s->name, v, mtime_lo());
            break;
        }
        case OP_EXPECT:
            v = REG32(a);
            printf("OCA_REG %u %s 0x%08x t=%u\n", i, s->name, v, mtime_lo());
            if ((v & s->mask) != s->value) {
                printf("FAIL: step %u: %s is 0x%08x, expected 0x%08x under mask 0x%08x\n",
                       i, s->name, v & s->mask, s->value, s->mask);
                return 1;
            }
            break;
        case OP_WAIT: {
            const uint32_t t0 = mtime_lo();
            while (mtime_lo() - t0 < s->value) { }
            break;
        }
        default:
            break;
        }
    }
    printf("PASS: OCA regscript die0 (SMC side)\n");
    return 0;
}
