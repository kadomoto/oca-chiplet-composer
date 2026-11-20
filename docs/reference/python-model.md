# Python model API

A chiplet's logic model is a Python class named `Model` that extends `RegisterModel`. The runtime (`usermodel/runtime.py`) gives every register its [default behaviour](register-map.md#access-types); the model overrides only what the logic adds.

```python
class Model(RegisterModel):
    def setup(self): ...
    def update(self): ...
    def on_write(self, reg, value): ...
    def on_read(self, reg): return None
```

`RegisterModel`, `Register` and `math` are available without imports.

## Hooks

| Hook | Called | Use it to |
|---|---|---|
| `setup()` | once, before the first access | create the model's own state |
| `update()` | before every access, with `self.t_ns` already set | finish time-dependent work: check whether a deadline has passed |
| `on_write(reg, value)` | after the default write behaviour | start work when firmware writes a command |
| `on_read(reg)` | before the default read | return a value to override the read, or `None` to keep it |

There is no clock callback. Instead, `update()` runs on every access with the simulation time, so behaviour such as "DONE 200 ns after START" is evaluated lazily: store a deadline in `on_write`, check it in `update`.

## Attributes and helpers

| Name | Meaning |
|---|---|
| `self["NAME"]` | the register named NAME |
| `self.t_ns` | simulation time of the current access, in ns |
| `self.params` | the register map's `params` |
| `self.delay_ns` | delay to add to the current access; reset to `access_ns` before each one |
| `self.log(msg)` | print into the simulation log, prefixed with the time |
| `self.to_u32(v)` | store a signed value as a 32-bit two's-complement register |

A `Register` has:

| Name | Meaning |
|---|---|
| `.name`, `.offset`, `.access` | from the map |
| `.value` | the stored 32-bit value |
| `.field(name)` | read a field |
| `.set_field(name, v)` | write a field |
| `.fifo` | a `collections.deque` for `fifo_w` and `fifo_r` registers |

An exception in a hook is logged and the access is answered as a bus error. The SMC's instruction-set simulator stops on a failed access, so the run ends there; the model log names the exception.

## Example

```python
--8<-- "summer_model.py"
```
