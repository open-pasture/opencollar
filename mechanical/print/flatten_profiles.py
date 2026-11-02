"""Flatten OrcaSlicer's bundled printer profiles (which inherit from base
files) into standalone JSON the CLI can load, with our overrides.

    python3 flatten_profiles.py          # Ender-3 V3 SE, PLA quick look -> ender3v3se/{machine,process,filament}.json
    python3 flatten_profiles.py petg     # Ender-3 V3 SE, PETG working parts -> ender3v3se_petg/
    python3 flatten_profiles.py p2s_asa  # Bambu Lab P2S, ASA working parts -> p2s_asa/
    python3 flatten_profiles.py p2s_pla  # Bambu Lab P2S, PLA fit checks -> p2s_pla/
"""
import json
import os
import sys

PROFILES = "/Applications/OrcaSlicer.app/Contents/Resources/profiles"
MODE = sys.argv[1] if len(sys.argv) > 1 else ""
ORCA = os.path.join(PROFILES, "BBL" if MODE.startswith("p2s") else "Creality")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   {"petg": "ender3v3se_petg", "p2s_asa": "p2s_asa", "p2s_pla": "p2s_pla"}.get(MODE, "ender3v3se"))

SOURCES = {
    "machine": ("machine", "Creality Ender-3 V3 SE 0.4 nozzle"),
    "process": ("process", "0.24mm Draft @Creality Ender3V3SE 0.4"),
    "filament": ("filament", "Creality Generic PLA @Ender-3V3-all"),
}

# Quick look in PLA: checks size, fit and layout, not strength. Thick
# layers, hollow walls (0 % infill: the outside looks the same) and light
# grid supports, which here print about twice as fast as tree supports.
OVERRIDES = {
    "process": {
        "layer_height": "0.28",
        "wall_loops": "2",
        "top_shell_layers": "3",
        "bottom_shell_layers": "2",
        "sparse_infill_density": "0%",
        "enable_support": "1",
        "support_type": "normal(auto)",
        "support_threshold_angle": "30",
        "support_base_pattern": "rectilinear",
        "support_base_pattern_spacing": "4",
        "support_top_z_distance": "0.28",
        "support_interface_top_layers": "2",
        "support_interface_spacing": "0.8",
        "support_speed": "150",
        "support_interface_speed": "80",
        "brim_type": "auto_brim",
    },
}

# Working parts (node V1): thick walls and solid tops seal and take heat-set
# inserts; tree supports only where the cap's underside relief needs them.
WORKING = {
    "process": {
        "wall_loops": "6",
        "top_shell_layers": "6",
        "bottom_shell_layers": "6",
        "sparse_infill_density": "40%",
        "sparse_infill_pattern": "gyroid",
        "enable_support": "1",
        "support_type": "tree(auto)",
        "support_threshold_angle": "40",
        "brim_type": "auto_brim",
    },
}

# PETG on the Ender: the V3 SE has no enclosure, so ASA would warp there.
if MODE == "petg":
    SOURCES["process"] = ("process", "0.20mm Standard @Creality Ender3V3SE 0.4")
    SOURCES["filament"] = ("filament", "Creality Generic PETG @Ender-3V3-all")
    OVERRIDES = WORKING

# ASA on the enclosed P2S: UV- and heat-stable shells for animals outdoors.
if MODE == "p2s_asa":
    SOURCES = {
        "machine": ("machine", "Bambu Lab P2S 0.4 nozzle"),
        "process": ("process", "0.20mm Standard @BBL P2S"),
        "filament": ("filament", "Bambu ASA @BBL P2S 0.4 nozzle"),
    }
    # ASA won't print on the default Cool Plate; the P2S ships with textured PEI.
    OVERRIDES = {"process": dict(WORKING["process"], curr_bed_type="Textured PEI Plate")}

# PLA on the P2S while the ASA is in transit: fit and placement only, never
# on an animal. Standard layers so holes come out true, light walls and
# infill for speed; hole sizes still differ from ASA.
if MODE == "p2s_pla":
    SOURCES = {
        "machine": ("machine", "Bambu Lab P2S 0.4 nozzle"),
        "process": ("process", "0.20mm Standard @BBL P2S"),
        "filament": ("filament", "Generic PLA @BBL P2S"),
    }
    OVERRIDES = {"process": {
        "wall_loops": "3",
        "sparse_infill_density": "15%",
        "enable_support": "1",
        "support_type": "tree(auto)",
        "support_threshold_angle": "40",
        "curr_bed_type": "Textured PEI Plate",
    }}


def load(kind, name):
    for folder in (os.path.join(ORCA, kind), ORCA):
        path = os.path.join(folder, name + ".json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            parent = data.get("inherits")
            if parent:
                merged = load(kind, parent)
                merged.update(data)
                data = merged
            return data
    raise FileNotFoundError(f"{kind}/{name}")


os.makedirs(OUT, exist_ok=True)
for key, (kind, name) in SOURCES.items():
    data = load(kind, name)
    data.pop("inherits", None)
    data.update(OVERRIDES.get(key, {}))
    # The CLI matches presets through the printer's system parent: keep the
    # machine inheriting from the bundled preset and list that parent as the
    # compatible printer for the process and filament.
    printer = SOURCES["machine"][1]
    if key == "machine":
        data["inherits"] = printer
    else:
        data["compatible_printers"] = [printer]
        data["compatible_printers_condition"] = ""
    data["from"] = "User"
    data["is_custom_defined"] = "0"
    data["name"] = f"OpenCollar {key} ({name})"
    with open(os.path.join(OUT, f"{key}.json"), "w") as f:
        json.dump(data, f, indent=2)
    print("wrote", key, "keys:", len(data))
