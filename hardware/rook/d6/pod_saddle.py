"""D8 neck saddle + sealed blank shock-bay cover (per pod).

Pilot = production: leave room for the completed shock module on this design.
Module envelope is PLACEHOLDER pending op-firmware — do not populate.

Print (saddle): flat pod-mating face on bed (z=0); concave R220 neck-face UP;
light supports in the bowl. Curved face never on the bed.

Print (bay cover): flat, features UP, PLA or ASA.

Run:
  cd hardware/rook/d6
  blender --background --factory-startup --python pod_saddle.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..", "common", "cad", "lib")))
sys.path.insert(0, _HERE)

import assembly as A  # noqa: E402
import oc  # noqa: E402

OUT = os.path.join(_HERE, "stl")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# PLACEHOLDER — pending op-firmware (shock module envelope)
# ---------------------------------------------------------------------------
MODULE_PLACEHOLDER = True
MODULE_L = 40.0          # along strap (Y), mm
MODULE_W = 25.0          # across strap (X), mm
MODULE_H = 8.0           # depth into saddle / toward neck, mm
ELECTRODE_D = 6.0        # pass-through diameter, mm
ELECTRODE_SPACING = 25.0  # centre-to-centre along Y, mm
ELECTRODE_LAND_D = 10.0  # flat/domed contact land OD, mm
ELECTRODE_CSINK_D = 8.0  # sealing countersink OD, mm
ELECTRODE_CSINK_H = 1.2
WIRE_CH_D = 6.0          # bay → cell-cavity channel
WIRE_GLAND_D = 10.0      # gland recess OD
WIRE_GLAND_H = 2.0
# Compliance reserve (unpopulated): spring/elastomer travel for electrode studs
ELECTRODE_COMPLIANCE_TRAVEL = 3.0  # mm reserved above land — do not rigid-lock to R220
# ---------------------------------------------------------------------------

SADDLE_R = 220.0         # neck-side concave radius, mm
SADDLE_L = 97.0          # along strap — matches pod footprint / gap chord
SADDLE_W = 52.0          # across — covers channel + lands, ≤ pod mid 68
SADDLE_FLAT_T = 2.0      # flat slab thickness at edges (above sagitta bowl)
SADDLE_PLAN_R = 3.0
BAY_WALL = 2.0
GASKET_W = 2.0
GASKET_D = 1.2
COVER_T = 2.0
COVER_SCREW_D = 3.4      # M3 clear
COVER_SCREW_SPAN_X = 16.0
COVER_SCREW_SPAN_Y = 28.0
MOUNT_SCREW_D = 3.4      # saddle → pod M3 clear
MOUNT_SPAN_X = 18.0
MOUNT_SPAN_Y = 32.0


def _sagitta(R: float, half_chord: float) -> float:
    return float(R - math.sqrt(max(R * R - half_chord * half_chord, 0.0)))


def _concave_neck_cut(body, R, length, width, z_flat):
    """Cut a concave cylindrical trough (axis = X) into the neck face.

    Chord along Y (=length). Depth = sagitta of R over length/2.
    """
    half = 0.5 * length
    sag = _sagitta(R, half)
    # Cylinder axis along X, centre below the flat so the trough depth = sag
    # At y=0 the cut reaches z_flat - sag; at y=±half it kisses z_flat.
    cyl_z = z_flat - sag + R
    cutter = oc.cylinder(
        "neck_R_cut",
        2.0 * R,
        width + 8.0,
        at=(0.0, 0.0, cyl_z),
        axis="X",
        segments=96,
        anchor="center",
    )
    # Limit cut to the neck side of the slab (don't eat the flat top)
    keep = oc.box(
        "neck_keep",
        (width + 10.0, length + 10.0, sag + 2.0),
        at=(0.0, 0.0, z_flat - sag - 1.0),
        anchor="bottom",
    )
    oc.intersect(cutter, keep)
    oc.cut(body, cutter)
    return sag


def saddle_body(side: str = "L"):
    """Flat-top / R220-concave-bottom saddle with sealed blank bay."""
    # Build in print frame: flat pod face at z=0 (bed); neck face +Z.
    # Assembled: rotate 180° about X so neck faces the animal (world −radial).
    sag = _sagitta(SADDLE_R, 0.5 * SADDLE_L)
    total_h = SADDLE_FLAT_T + sag + MODULE_H * 0.15  # small extra for bay floor
    # Bay needs MODULE_H inside the saddle. Available toward neck ≈ sag (~5.4).
    # If MODULE_H > sag + SADDLE_FLAT_T - walls, height grows toward neck only.
    bay_need = MODULE_H + BAY_WALL + GASKET_D + 0.5
    extra = max(0.0, bay_need - (sag + SADDLE_FLAT_T))
    total_h = SADDLE_FLAT_T + sag + extra

    body = oc.rounded_rect(
        f"pod_{side}_saddle",
        (SADDLE_W, SADDLE_L, total_h),
        SADDLE_PLAN_R,
        at=(0.0, 0.0, 0.0),
        anchor="bottom",
        segments=12,
    )
    # Concave neck face from the top of the slab downward
    z_flat_top = total_h
    # Full 97 mm chord so sagitta ≈5.4 mm matches flat-underside gap fill
    sag_cut = _concave_neck_cut(body, SADDLE_R, SADDLE_L - 0.5, SADDLE_W - 2.0, z_flat_top)
    # Re-flat a rim so the outer land stays printable / seals
    rim = oc.rounded_rect(
        "saddle_rim",
        (SADDLE_W, SADDLE_L, SADDLE_FLAT_T),
        SADDLE_PLAN_R,
        at=(0.0, 0.0, 0.0),
        anchor="bottom",
        segments=10,
    )
    oc.union(body, rim)

    # --- shock bay (empty) in saddle centre, opening to neck face (+Z) ---
    bay_z0 = total_h - sag_cut - MODULE_H
    if bay_z0 < SADDLE_FLAT_T + 0.5:
        bay_z0 = SADDLE_FLAT_T + 0.5
    oc.cut(
        body,
        oc.rounded_rect(
            "shock_bay",
            (MODULE_W, MODULE_L, MODULE_H + 1.0),
            2.0,
            at=(0.0, 0.0, bay_z0),
            anchor="bottom",
            segments=8,
        ),
    )
    # Gasket seat around bay (on neck-facing deck)
    gw = MODULE_W + 2.0 * (BAY_WALL + GASKET_W)
    gl = MODULE_L + 2.0 * (BAY_WALL + GASKET_W)
    ring_o = oc.rounded_rect("gask_o", (gw, gl, GASKET_D), 2.5,
                             at=(0.0, 0.0, total_h - sag_cut - GASKET_D), anchor="bottom")
    ring_i = oc.rounded_rect(
        "gask_i",
        (MODULE_W + 2.0 * BAY_WALL, MODULE_L + 2.0 * BAY_WALL, GASKET_D + 0.4),
        2.0,
        at=(0.0, 0.0, total_h - sag_cut - GASKET_D - 0.1),
        anchor="bottom",
    )
    oc.cut(body, oc.cut(ring_o, ring_i))

    # Electrode pass-throughs on neck face — compliance travel reserved (unpopulated)
    for i, sy in enumerate((-0.5, 0.5)):
        ey = sy * ELECTRODE_SPACING
        # Through-hole
        oc.cut(
            body,
            oc.cylinder(
                f"elec_h{i}",
                ELECTRODE_D,
                total_h + 4.0,
                at=(0.0, ey, total_h * 0.5),
                anchor="center",
                segments=24,
            ),
        )
        # Countersink for seal on neck face
        oc.cut(
            body,
            oc.cylinder(
                f"elec_cs{i}",
                ELECTRODE_CSINK_D,
                ELECTRODE_CSINK_H + 0.2,
                at=(0.0, ey, total_h - sag_cut - ELECTRODE_CSINK_H),
                anchor="bottom",
                segments=24,
            ),
        )
        # Flat contact land (slight dome via shallow cylinder boss around hole)
        land = oc.cylinder(
            f"elec_land{i}",
            ELECTRODE_LAND_D,
            0.6,
            at=(0.0, ey, total_h - sag_cut - 0.3),
            anchor="bottom",
            segments=24,
        )
        oc.union(body, land)
        # Compliance well (extra depth for spring/elastomer — empty)
        oc.cut(
            body,
            oc.cylinder(
                f"elec_comp{i}",
                ELECTRODE_LAND_D - 1.0,
                ELECTRODE_COMPLIANCE_TRAVEL,
                at=(0.0, ey, bay_z0 + MODULE_H - ELECTRODE_COMPLIANCE_TRAVEL),
                anchor="bottom",
                segments=20,
            ),
        )

    # Wiring path: Ø6 channel from bay toward +Y (cap/mount end) then up to pod face
    # Horizontal run in bay floor plane
    oc.cut(
        body,
        oc.cylinder(
            "wire_run",
            WIRE_CH_D,
            MODULE_L * 0.5 + 18.0,
            at=(0.0, MODULE_L * 0.25 + 8.0, bay_z0 + WIRE_CH_D * 0.5 + 0.5),
            axis="Y",
            segments=20,
        ),
    )
    # Vertical gland to flat pod face (z=0)
    oc.cut(
        body,
        oc.cylinder(
            "wire_up",
            WIRE_CH_D,
            bay_z0 + 4.0,
            at=(0.0, MODULE_L * 0.5 + 10.0, 0.0),
            anchor="bottom",
            segments=20,
        ),
    )
    oc.cut(
        body,
        oc.cylinder(
            "wire_gland",
            WIRE_GLAND_D,
            WIRE_GLAND_H + 0.2,
            at=(0.0, MODULE_L * 0.5 + 10.0, 0.0),
            anchor="bottom",
            segments=20,
        ),
    )

    # Cover screw bosses (M3 clear) around bay
    for i, (sx, sy) in enumerate((
        (-1, -1), (1, -1), (-1, 1), (1, 1),
    )):
        oc.cut(
            body,
            oc.cylinder(
                f"cover_h{i}",
                COVER_SCREW_D,
                total_h + 2.0,
                at=(sx * COVER_SCREW_SPAN_X * 0.5, sy * COVER_SCREW_SPAN_Y * 0.5, total_h * 0.5),
                anchor="center",
                segments=16,
            ),
        )

    # Saddle → pod mount holes (from flat face)
    for i, (sx, sy) in enumerate((
        (-1, -1), (1, -1), (-1, 1), (1, 1),
    )):
        oc.cut(
            body,
            oc.cylinder(
                f"mnt_h{i}",
                MOUNT_SCREW_D,
                SADDLE_FLAT_T + 6.0,
                at=(sx * MOUNT_SPAN_X, sy * MOUNT_SPAN_Y, 0.0),
                anchor="bottom",
                segments=16,
            ),
        )

    oc.bake(body)
    oc.move(body, dz=-oc.bounds(body)[0][2])
    meta = {
        "side": side,
        "saddle_R_mm": SADDLE_R,
        "sagitta_mm": round(sag_cut, 2),
        "total_h_mm": round(list(oc.size(body))[2], 2),
        "extra_toward_neck_mm": round(extra, 2),
        "height_above_strap_mm": 0.0,
        "module_placeholder": {
            "flag": MODULE_PLACEHOLDER,
            "L_W_H_mm": [MODULE_L, MODULE_W, MODULE_H],
            "pending": "op-firmware",
        },
        "electrode_compliance_travel_mm": ELECTRODE_COMPLIANCE_TRAVEL,
        "print": {
            "orientation": "flat pod-face on bed; concave neck-face UP; light bowl supports",
            "why": "mating/seal face gets bed accuracy; curve never on bed",
            "material": "ASA",
            "brim_mm": 8,
        },
    }
    return body, meta


def bay_cover(side: str = "L"):
    """Blank cover plate — seals empty bay (IP path with gasket)."""
    gw = MODULE_W + 2.0 * BAY_WALL + 1.0
    gl = MODULE_L + 2.0 * BAY_WALL + 1.0
    cover = oc.rounded_rect(
        f"pod_{side}_bay_cover",
        (gw, gl, COVER_T),
        2.0,
        at=(0.0, 0.0, 0.0),
        anchor="bottom",
        segments=8,
    )
    for i, (sx, sy) in enumerate((
        (-1, -1), (1, -1), (-1, 1), (1, 1),
    )):
        oc.cut(
            cover,
            oc.cylinder(
                f"bc_h{i}",
                COVER_SCREW_D,
                COVER_T + 2.0,
                at=(sx * COVER_SCREW_SPAN_X * 0.5, sy * COVER_SCREW_SPAN_Y * 0.5, -0.5),
                anchor="bottom",
                segments=16,
            ),
        )
    # Outer label: BLANK (deboss)
    try:
        import build_d5 as d5
        d5.emboss_label(cover, "BLANK", (0.0, 0.0, COVER_T), rot_z=0.0)
    except Exception:
        pass
    oc.bake(cover)
    oc.move(cover, dz=-oc.bounds(cover)[0][2])
    return cover


def _export(obj, path):
    oc.prepare_for_export(obj, merge=1e-4)
    oc.export_stl(obj, path)
    dims = list(oc.size(obj))
    wt = oc.check_stl_watertight(path)
    print(("OK" if wt.get("watertight") else "LOOK"), path, [round(d, 1) for d in dims], wt)
    return dims, wt


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {
        "revision": "D8_saddle_shock_bay",
        "module_placeholder": {
            "MODULE_L": MODULE_L,
            "MODULE_W": MODULE_W,
            "MODULE_H": MODULE_H,
            "ELECTRODE_D": ELECTRODE_D,
            "ELECTRODE_SPACING": ELECTRODE_SPACING,
            "pending": "op-firmware",
        },
        "bodies": {},
        "part_count_delta": {
            "per_pod_was": 2,
            "per_pod_now": 4,
            "added": ["pod_*_saddle", "pod_*_bay_cover"],
            "collar_added_qty": 4,
        },
        "pass": True,
    }
    sag_ref = _sagitta(SADDLE_R, 0.5 * SADDLE_L)
    height_note = (
        f"R{SADDLE_R:.0f} sagitta≈{sag_ref:.2f} mm fills flat-underside gap; "
        f"MODULE_H={MODULE_H} mm "
    )
    if MODULE_H > sag_ref:
        height_note += (
            f"— module deeper than sagitta by {MODULE_H - sag_ref:.1f} mm; "
            "extra grows toward neck only (0 mm above strap)."
        )
    else:
        height_note += "— fits inside saddle gap; 0 mm above strap."
    report["height"] = {
        "above_strap_mm": 0.0,
        "toward_neck_mm": round(sag_ref, 2),
        "note": height_note,
    }

    for side in ("L", "R"):
        oc.reset()
        sad, meta = saddle_body(side)
        path = os.path.join(OUT, f"pod_{side}_saddle.stl")
        dims, wt = _export(sad, path)
        report["bodies"][f"pod_{side}_saddle"] = {
            "size_mm": dims, "watertight": wt, **meta,
        }
        if not wt.get("watertight"):
            report["pass"] = False

        oc.reset()
        cov = bay_cover(side)
        path = os.path.join(OUT, f"pod_{side}_bay_cover.stl")
        dims, wt = _export(cov, path)
        report["bodies"][f"pod_{side}_bay_cover"] = {
            "size_mm": dims, "watertight": wt,
            "print": {"orientation": "flat; label UP", "material": "ASA or PLA"},
        }
        if not wt.get("watertight"):
            report["pass"] = False

    with open(os.path.join(OUT, "pod_saddle_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("HEIGHT:", height_note)
    print("PASS" if report["pass"] else "FAIL")
    return report


if __name__ == "__main__":
    main()
