"""Runtime for chiplet logic models written in Python.

mdie-vp's py_bridge starts this as a child process and sends one line per access
to the chiplet's logic window (see vp/platform/smu/inc/user_port.h):

    R <offset hex> <len hex> <time_ns>          -> OK <value hex> <delay_ns>
    W <offset hex> <len hex> <value hex> <time_ns> -> OK 0 <delay_ns>
    Q                                            (end of simulation)

The register map (JSON, written by the composer) gives every register a default
behaviour by access type, so a model works before any Python is written:

    rw      read/write storage           ro      read-only (model sets it)
    wo      write-only, reads return 0   w1c     write 1 to clear
    fifo_w  each write pushes a word     fifo_r  each read pops a word (0 if empty)

A model file defines `class Model(RegisterModel)` and overrides what it needs:

    update()               called before every access, with self.t_ns already set:
                           evaluate time-dependent behaviour lazily here
    on_write(reg, value)   after the default write behaviour
    on_read(reg)           return a value to override the default read, or None

Usage: python3 runtime.py --regmap regmap.json [--model model.py] [--trace trace.jsonl]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import deque

ACCESS = {"rw", "ro", "wo", "w1c", "fifo_w", "fifo_r"}


class Register:
    def __init__(self, d: dict):
        self.name = d["name"]
        self.offset = int(d["offset"])
        self.access = d.get("access", "rw")
        self.reset = int(d.get("reset", 0)) & 0xFFFFFFFF
        self.fields = {f["name"]: (int(f["lsb"]), int(f.get("width", 1))) for f in d.get("fields", [])}
        self.value = self.reset
        self.fifo: deque[int] = deque()

    def field(self, name: str) -> int:
        lsb, w = self.fields[name]
        return (self.value >> lsb) & ((1 << w) - 1)

    def set_field(self, name: str, v: int) -> None:
        lsb, w = self.fields[name]
        m = ((1 << w) - 1) << lsb
        self.value = (self.value & ~m) | ((int(v) << lsb) & m)


class RegisterModel:
    """Base class: default register behaviour plus hooks for the model's own logic."""

    def __init__(self, regmap: dict):
        self.regmap = regmap
        self.params = dict(regmap.get("params", {}))
        self.regs = {r["name"]: Register(r) for r in regmap["registers"]}
        self.by_offset = {r.offset: r for r in self.regs.values()}
        self.t_ns = 0.0
        self.delay_ns = float(regmap.get("access_ns", 2.0))
        self.setup()

    # ---- hooks for models
    def setup(self) -> None: ...
    def update(self) -> None: ...
    def on_write(self, reg: Register, value: int) -> None: ...
    def on_read(self, reg: Register) -> int | None: return None

    # ---- helpers for models
    def __getitem__(self, name: str) -> Register:
        return self.regs[name]

    def log(self, msg: str) -> None:
        print(f"[model {self.t_ns:.1f} ns] {msg}", file=sys.stderr, flush=True)

    @staticmethod
    def to_u32(v: float | int) -> int:
        """Store a signed value (e.g. dBm) as a 32-bit two's-complement register."""
        return int(round(v)) & 0xFFFFFFFF

    # ---- protocol side
    def read(self, off: int) -> int:
        r = self.by_offset.get(off)
        if r is None:
            raise KeyError(f"no register at offset 0x{off:x}")
        self.update()
        v = self.on_read(r)
        if v is None:
            if r.access == "fifo_r":
                v = r.fifo.popleft() if r.fifo else 0
            elif r.access == "wo":
                v = 0
            else:
                v = r.value
        return int(v) & 0xFFFFFFFF

    def write(self, off: int, value: int) -> None:
        r = self.by_offset.get(off)
        if r is None:
            raise KeyError(f"no register at offset 0x{off:x}")
        self.update()
        value &= 0xFFFFFFFF
        if r.access in ("rw", "wo"):
            r.value = value
        elif r.access == "w1c":
            r.value &= ~value
        elif r.access == "fifo_w":
            r.fifo.append(value)
        # ro, fifo_r: writes are ignored by default
        self.on_write(r, value)


def load_model(path: str | None, regmap: dict) -> RegisterModel:
    if not path:
        return RegisterModel(regmap)
    spec = importlib.util.spec_from_file_location("chiplet_model", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__.update(RegisterModel=RegisterModel, Register=Register, math=math)
    spec.loader.exec_module(mod)
    return getattr(mod, "Model", RegisterModel)(regmap)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regmap", required=True)
    ap.add_argument("--model")
    ap.add_argument("--trace")
    a = ap.parse_args()
    regmap = json.load(open(a.regmap))
    model = load_model(a.model, regmap)
    names = {r.offset: r.name for r in model.regs.values()}
    trace = open(a.trace, "w") if a.trace else None
    model.log(f"{regmap.get('name', 'model')}: {len(model.regs)} registers ready")
    for line in sys.stdin:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "Q":
            break
        try:
            if parts[0] == "R":
                off, t = int(parts[1], 16), float(parts[3])
                model.t_ns = t
                model.delay_ns = float(regmap.get("access_ns", 2.0))
                v = model.read(off)
                print(f"OK {v:x} {model.delay_ns}", flush=True)
                op = "read"
            elif parts[0] == "W":
                off, v, t = int(parts[1], 16), int(parts[3], 16), float(parts[4])
                model.t_ns = t
                model.delay_ns = float(regmap.get("access_ns", 2.0))
                model.write(off, v)
                print(f"OK 0 {model.delay_ns}", flush=True)
                op = "write"
            else:
                print("ERR unknown request", flush=True)
                continue
            if trace:
                trace.write(json.dumps({"t_ns": round(t, 3), "op": op, "reg": names.get(off, hex(off)),
                                        "value": v}) + "\n")
                trace.flush()
        except Exception as e:  # noqa: BLE001 - report to the VP as a bus error
            model.log(f"error: {e!r}")
            print(f"ERR {type(e).__name__}", flush=True)
    model.log("simulation ended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
