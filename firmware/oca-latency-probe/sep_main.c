/* SPDX-License-Identifier: Apache-2.0 */
/* SEP half of the latency probe: boot and print a banner. */
extern int printf(const char *format, ...);
int main(void)
{
    printf("PASS: OCA latency probe (SEP side)\n");
    return 0;
}
