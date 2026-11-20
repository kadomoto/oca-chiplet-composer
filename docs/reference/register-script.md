# Register scripts

A register script is the firmware a chiplet runs against its own logic: a few lines, one step per line, checked against the register map and compiled into a table that `firmware/oca-regscript` executes on the chiplet's SMC.

```text
write IN_FIFO 1
write CTRL START          # a field name sets that field's bits
poll STATUS.DONE          # wait until DONE is set
read RESULT
expect RESULT 10
```

## Steps

| Step | Does |
|---|---|
| `write REG VALUE` | writes a number (decimal, `0x` hex, or negative) |
| `write REG FIELD[\|FIELD…]` | writes a value with all bits of the named fields set |
| `read REG` | reads and reports the value |
| `poll REG.FIELD [VALUE] [timeout N]` | reads until the field equals VALUE (default: all its bits set); fails after N reads (default 200000) |
| `poll REG VALUE [timeout N]` | the same for the whole register |
| `expect REG[.FIELD] VALUE` | reads, reports, and fails the run if the value differs |
| `wait NS` | waits NS nanoseconds of CLINT time |

`#` starts a comment. Names are checked against the map; an unknown register or field is a design rule error that names the line.

## Output

Every `read`, `poll` and `expect` reports a line the composer parses into **Last run**:

```text
OCA_REG <step> <name> 0x<value> t=<mtime>
```

`poll` timeouts and `expect` mismatches print `FAIL: step N: …` and stop the script.
