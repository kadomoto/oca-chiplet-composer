# Register maps

A register map describes a chiplet's own logic: the registers firmware sees in the chiplet's logic window, and how each behaves before any Python is written. It is one JSON object, edited in the **Chiplet logic** tab.

```json
{
  "name": "summer",
  "window_size": 4096,
  "access_ns": 4,
  "params": {"ns_per_word": 50},
  "registers": [
    {"name": "CTRL", "offset": 0, "access": "rw", "reset": 0, "doc": "START adds up the words",
     "fields": [{"name": "START", "lsb": 0, "width": 1}]}
  ]
}
```

## Fields

| Key | Default | Meaning |
|---|---|---|
| `name` | | the logic's name; prefixes the C header's macros |
| `window_size` | `4096` | bytes, a power of two up to 16 MiB |
| `access_ns` | `4` | delay added to every access, in ns (a model can change it per access) |
| `params` | `{}` | values the model reads as `self.params`; edited as `name = value` lines |
| `registers` | | the registers below |

Each register:

| Key | Default | Meaning |
|---|---|---|
| `name` | | a C identifier, unique in the map |
| `offset` | | bytes from the window base, a multiple of 4, unique |
| `access` | `rw` | one of the access types below |
| `reset` | `0` | value at reset |
| `fields` | `[]` | named bit ranges: `{"name", "lsb", "width"}`, inside 32 bits, not overlapping |
| `doc` | `""` | a description; it goes into the C header as a comment |

## Access types

| Access | Read | Write |
|---|---|---|
| `rw` | the value | stores the value |
| `ro` | the value (the model sets it) | ignored |
| `wo` | `0` | stores the value |
| `w1c` | the value | clears the bits written as 1 |
| `fifo_w` | the stored value | pushes the value into the register's FIFO |
| `fifo_r` | pops from the register's FIFO (`0` when empty) | ignored |

A model's hooks run after these defaults and can override them; see [Python model API](python-model.md).

## Generated C header

The composer generates a header for firmware from the map. For a map named `summer`:

```c
#define SUMMER_BASE 0x70000000ULL   /* chiplet logic window, die-local */
#define SUMMER_SIZE 0x1000u
#define SUMMER_CTRL_OFF 0x000u   /* rw: START adds up the words */
#define SUMMER_CTRL (*(volatile uint32_t *)(uintptr_t)(SUMMER_BASE + SUMMER_CTRL_OFF))
#define SUMMER_CTRL_START_SHIFT 0u
#define SUMMER_CTRL_START_MASK  0x00000001u
```

The window is die-local: every chiplet with logic has its own at `0x7000_0000`, reached by that chiplet's firmware.
