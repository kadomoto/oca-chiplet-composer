"""Component / package / interconnect catalog for the OCA Chiplet Composer.

All physical numbers are *illustrative defaults* (editable in the GUI). They are
loosely based on public UCIe 1.1/2.0 targets and are not Tenstorrent data.
"""

import json
from pathlib import Path

# Every OCA-compliant chiplet carries the Harness (SMC + SEP + SMU + AoU).
HARNESS_SUBSYSTEMS = ["SMC", "SEP", "SMU", "AoU"]

CHIPLET_TEMPLATES = [
    {
        "kind": "io",
        "label": "IO / Host chiplet",
        "color": "#4f7cff",
        "w_mm": 8.0, "h_mm": 6.0,
        "ucie_ports": 4,
        "power_w": 15.0,
        "harness": HARNESS_SUBSYSTEMS,
        "vp_role": "smu",          # simulated by smu-vp
        "notes": "PCIe/Ethernet + boot master. Root of secure boot.",
    },
    {
        "kind": "compute",
        "label": "Compute chiplet",
        "color": "#e0723a",
        "w_mm": 10.0, "h_mm": 10.0,
        "ucie_ports": 4,
        "power_w": 60.0,
        "harness": HARNESS_SUBSYSTEMS,
        "vp_role": "smu",
        "notes": "AI / CPU tiles behind the Harness SMN.",
    },
    {
        "kind": "memory",
        "label": "Memory chiplet",
        "color": "#2fa37a",
        "w_mm": 7.0, "h_mm": 9.0,
        "ucie_ports": 2,
        "power_w": 12.0,
        "harness": HARNESS_SUBSYSTEMS,
        "vp_role": "smu",
        "notes": "LPDDR/HBM controller chiplet.",
    },
    {
        "kind": "harness",
        "label": "Harness-only test die",
        "color": "#8a63d2",
        "w_mm": 4.0, "h_mm": 4.0,
        "ucie_ports": 1,
        "power_w": 2.0,
        "harness": HARNESS_SUBSYSTEMS,
        "vp_role": "smu",
        "notes": "Minimal die: Harness only. Maps 1:1 to today's smu-vp.",
    },
]

# A chiplet with its own logic modelled in Python (usermodel/examples).
_EX = Path(__file__).resolve().parent.parent / "usermodel" / "examples"


def _example_logic(stem: str) -> dict:
    return {"enabled": True,
            "regmap": json.loads((_EX / f"{stem}.json").read_text()),
            "model": (_EX / f"{stem}_model.py").read_text(),
            "script": (_EX / f"{stem}_script.txt").read_text()}


CHIPLET_TEMPLATES.append({
    "kind": "radio",
    "label": "Radio chiplet (60 GHz)",
    "color": "#c2410c",
    "w_mm": 5.0, "h_mm": 5.0,
    "ucie_ports": 2,
    "power_w": 3.0,
    "harness": HARNESS_SUBSYSTEMS,
    "vp_role": "smu",
    "notes": "Wireless chiplet-to-chiplet link. Its logic is a Python model behind a register map.",
    "logic": _example_logic("radio"),
})

# Starting point when a person enables logic on any other chiplet.
EMPTY_LOGIC = {
    "enabled": True,
    "regmap": {"name": "logic", "window_size": 4096, "access_ns": 4, "params": {},
               "registers": [{"name": "CTRL", "offset": 0, "access": "rw", "reset": 0, "doc": "control",
                              "fields": [{"name": "START", "lsb": 0, "width": 1}]},
                             {"name": "STATUS", "offset": 4, "access": "ro", "reset": 0, "doc": "status",
                              "fields": [{"name": "DONE", "lsb": 0, "width": 1}]}]},
    "model": "",
    "script": "write CTRL START\nread STATUS\n",
}

# Package technologies. reach / pitch / energy from UCIe public targets.
PACKAGES = {
    "ucie-s-organic": {
        "label": "UCIe-S (standard organic, 2D)",
        "ucie_flavor": "standard",
        "max_reach_mm": 25.0,
        "bump_pitch_um": 110,
        "lanes_per_module": 16,
        "energy_pj_per_bit": 1.0,
        "min_die_gap_mm": 0.5,
        "flight_ps_per_mm": 7.0,
        "cost_per_mm2": 0.004,
    },
    "ucie-a-interposer": {
        "label": "UCIe-A (Si interposer, 2.5D)",
        "ucie_flavor": "advanced",
        "max_reach_mm": 2.0,
        "bump_pitch_um": 45,
        "lanes_per_module": 64,
        "energy_pj_per_bit": 0.5,
        "min_die_gap_mm": 0.1,
        "flight_ps_per_mm": 8.0,
        "cost_per_mm2": 0.03,
    },
    "ucie-a-bridge": {
        "label": "UCIe-A (embedded bridge, 2.5D)",
        "ucie_flavor": "advanced",
        "max_reach_mm": 2.0,
        "bump_pitch_um": 45,
        "lanes_per_module": 64,
        "energy_pj_per_bit": 0.5,
        "min_die_gap_mm": 0.1,
        "flight_ps_per_mm": 8.0,
        "cost_per_mm2": 0.012,
    },
}

DEFAULT_LINK = {
    "modules": 1,
    "data_rate_gtps": 16,
    "aou_fixed_ns": 6.0,     # AoU bridge + FDI/adapter (illustrative)
    "phy_ns": 2.0,           # UCIe PHY Tx+Rx
}

DEFAULT_PROCESS = {
    "defect_density_per_cm2": 0.1,
    "wafer_cost_usd": 17000,
    "wafer_diameter_mm": 300,
}
