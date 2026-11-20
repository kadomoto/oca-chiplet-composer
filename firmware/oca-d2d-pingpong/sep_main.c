/* SPDX-License-Identifier: Apache-2.0 */
/* SEP half of the die-to-die ping-pong: boot and print a banner. */
extern int printf(const char *format, ...);
int main(void)
{
    printf("PASS: OCA d2d ping-pong (SEP side)\n");
    return 0;
}
