"""Flatten OrcaSlicer's bundled Ender-3 V3 SE profiles (which inherit from
base files) into standalone JSON the CLI can load, with our overrides.

    python3 flatten_profiles.py   # writes ender3v3se/{machine,process,filament}.json
"""
import json
import os

ORCA = "/Applications/OrcaSlicer.app/Contents/Resources/profiles/Creality"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ender3v3se")

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
