"""D8 neck saddle + service lid + wire blank-plug (per pod).

Pilot = production (Cody, 2026-11-04): the bay must hold the *complete*
version. Pod-bay placement is a **working assumption** under that stance
(docs/BOTTOM-BAY.md and older CAD disagree — not treated as final).

All MODULE_*/DRIVER_*/WIRE_*/ELECTRODE_* sizes below are
**PLACEHOLDER, not a spec** — pending op-firmware. No module, driver, or
electrode has been chosen. Easy to revise for later seal/isolation/vent rules.

Unfitted bay (op-strategy): NO electrodes, NO pulse circuit.
Only: service lid (or blank plug), connector position, wire path with
strain relief, sealed pass-through (+ blank wire plug). Skin-contact
lands are BLANK/FLAT only. Electrode studs / pass-throughs = reserved
geometry only, sealed or blank when unfitted — never open holes.
Flag: op-architect asked to keep studs; op-strategy wants no electrodes
in the unfitted state → op-strategy to resolve.

Design guardrail (op-strategy / Halter look-alike): do NOT move toward a
narrow low bridge, soft rounded blending, raised ribbed bridge top, vent
slots at the pod–bridge joint, or glass-look flat pod tops. KEEP cap
dominant + faceted/segmented; blind groove stays a distinct step; plan
corners ≤ R3.

Print (saddle): flat pod-face on bed; concave R220 UP; light bowl supports.
Print (service lid / wire plug): flat, features UP.

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

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..", "common", "cad", "lib")))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "d5", "cad")))
sys.path.insert(0, _HERE)

import oc  # noqa: E402
import build_d5 as d5  # noqa: E402 — L/R glyphs on wire plugs

OUT = os.path.join(_HERE, "stl")
os.makedirs(OUT, exist_ok=True)

# ===========================================================================
# PLACEHOLDER, not a spec — pending op-firmware. Adjust freely; generous
# margins on all axes. Nothing here is a chosen part.
# ===========================================================================
MODULE_PLACEHOLDER = True          # PLACEHOLDER, not a spec
MODULE_NOTE = "placeholder, not a spec — no shock module chosen"
MODULE_L = 40.0                    # along strap (Y), mm
MODULE_W = 25.0                    # across (X), mm
MODULE_H = 8.0                     # depth toward neck, mm
MODULE_MARGIN_XY = 3.0             # keep-out margin each side XY
MODULE_MARGIN_Z = 2.0              # keep-out margin depth

DRIVER_PLACEHOLDER = True          # PLACEHOLDER, not a spec
DRIVER_NOTE = "placeholder, not a spec — no driver board chosen"
DRIVER_L = 35.0                    # along strap
DRIVER_W = 22.0
DRIVER_H = 6.0
DRIVER_MARGIN_XY = 3.0
DRIVER_MARGIN_Z = 2.0
# Driver keep-out sits toward +Y (cap/mount) of the module bay

ELECTRODE_PLACEHOLDER = True       # PLACEHOLDER, not a spec
ELECTRODE_NOTE = (
    "placeholder, not a spec — reserved geometry only; unfitted skin face is "
    "BLANK/FLAT (no electrodes, no open holes, no pulse circuit)"
)
ELECTRODE_D = 6.0
ELECTRODE_SPACING = 25.0
ELECTRODE_LAND_D = 10.0            # blank/flat skin-contact land diameter
ELECTRODE_STUD_KEEP_OUT = True     # reserved internal geometry (architect)
ELECTRODE_COMPLIANCE_TRAVEL = 3.0  # reserved for spring/elastomer when fitted
# Unfitted (op-strategy): NO electrodes, NO pulse. Skin land = blank/flat only.
# Studs/pass-throughs = reserved sealed keep-outs inside the bay, not open.
# Flag: op-architect wants studs kept; op-strategy wants none in unfitted state.

WIRE_PLACEHOLDER = True            # PLACEHOLDER, not a spec
WIRE_NOTE = (
    "placeholder, not a spec — pod-to-cap harness channel; count/gauge unknown; "
    "sized ≥8 conductors for ~4–6 signals/pod (enable, fault, current sense, "
    "module-detect, GND, HV rail) + spare; NOT a final pinout"
)
WIRE_CONDUCTORS_MIN = 8
WIRE_CH_D = 8.0                    # sealed channel OD (≥8 conductors + spare)
WIRE_GLAND_D = 12.0
WIRE_GLAND_H = 2.5
WIRE_STRAIN_RELIEF_L = 8.0         # axial strain-relief pocket length
WIRE_STRAIN_RELIEF_D = 10.0

# Reserved firmware-support features — NOT designs (keep-out pockets only)
CONNECTOR_KEEP_OUT = (12.0, 10.0, 6.0)   # L×W×H pocket for bay connector
CONNECTOR_HAS_SENSE_ID = True            # sense/ID line → unfitted reads not-fitted
CONNECTOR_NOTE = (
    "reserved feature, not a design — connector position with sense/ID so an "
    "unfitted bay reads as not-fitted"
)
HW_KILL_KEEP_OUT = (8.0, 6.0, 4.0)       # switch/jumper/fuse-link pocket
HW_KILL_NOTE = (
    "reserved feature, not a design — reachable hardware kill that cuts the "
    "driver rail independent of firmware (switch / jumper / fuse-link); "
    "accessible via service lid without opening the cell cavity"
)

# Welfare-reviewer TBD — revision hooks only (not modelled). Change these
# later without redesigning the bay layout; envelopes stay parametric.
SEAL_RULES_TBD = True              # gasket/land/compound TBD
ISOLATION_CLEARANCE_TBD_MM = 0.0   # creepage/clearance TBD → grow margins
VENT_RULES_TBD = True              # venting TBD → optional cut later
WELFARE_NOTE = (
    "seal, isolation distance, and venting come later from the welfare "
    "reviewer; adjust MODULE_/DRIVER_/WIRE_ margins and BAY_WALL / GASKET_* "
    "— do not hard-code a sealing scheme yet"
)
# ===========================================================================

SADDLE_R = 220.0
SADDLE_L = 97.0
SADDLE_W = 52.0
SADDLE_FLAT_T = 2.0
SADDLE_PLAN_R = 3.0
BAY_WALL = 2.0
GASKET_W = 2.0
GASKET_D = 1.2
COVER_T = 2.5                          # service lid thickness
COVER_SCREW_D = 3.4
COVER_SCREW_SPAN_X = 18.0              # overridden per-opening below
COVER_SCREW_SPAN_Y = 36.0              # overridden per-opening below
MOUNT_SCREW_D = 3.4
MOUNT_SPAN_X = 18.0
MOUNT_SPAN_Y = 32.0

# Review shell contract (height-neutral above strap)
REVIEW_POD_ROOF_MM = 25.0              # lid-top above strap outer (r19)


def _sagitta(R: float, half_chord: float) -> float:
    return float(R - math.sqrt(max(R * R - half_chord * half_chord, 0.0)))


def _bay_envelope():
    """Module keep-out with margins (adjustable)."""
    return (
        MODULE_W + 2.0 * MODULE_MARGIN_XY,
        MODULE_L + 2.0 * MODULE_MARGIN_XY,
        MODULE_H + MODULE_MARGIN_Z,
    )


def _driver_envelope():
    return (
        DRIVER_W + 2.0 * DRIVER_MARGIN_XY,
        DRIVER_L + 2.0 * DRIVER_MARGIN_XY,
        DRIVER_H + DRIVER_MARGIN_Z,
    )


def _concave_neck_cut(body, R, length, width, z_flat):
    half = 0.5 * length
    sag = _sagitta(R, half)
    cyl_z = z_flat - sag + R
    cutter = oc.cylinder(
        "neck_R_cut", 2.0 * R, width + 8.0,
        at=(0.0, 0.0, cyl_z), axis="X", segments=96, anchor="center",
    )
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
    """Flat→pod / R220-concave→neck saddle with complete-version bay keep-outs."""
    sag = _sagitta(SADDLE_R, 0.5 * SADDLE_L)
    bw, bl, bh = _bay_envelope()
    dw, dl, dh = _driver_envelope()
    # Layout along Y (must fit inside SADDLE_L=97):
    #   driver (+Y / toward cap) | module (centre-ish) | wire exit (−Y / strap
    #   end, aligned with pod.py POD_WIRE_GLAND_Y ≈ −28).
    bay_gap = 2.0
    span = bl + dl + bay_gap
    # Keep combined bays inside ±(0.5*SADDLE_L − wall)
    half_clear = 0.5 * SADDLE_L - BAY_WALL - 1.0
    if 0.5 * span > half_clear:
        # Should not happen with current PLACEHOLDER sizes; guard anyway.
        raise RuntimeError(
            f"module+driver span {span:.1f} exceeds saddle clear {2*half_clear:.1f}"
        )
    module_y = -0.5 * (dl + bay_gap)          # biased −Y so wire side has room
    driver_y = module_y + 0.5 * bl + 0.5 * dl + bay_gap
    # Wire gland on flat face — match pod.py POD_WIRE_GLAND_Y = −28
    wire_y = -28.0

    # Combined depth need: module + driver share saddle thickness (side-by-side)
    stack_need = max(bh, dh) + BAY_WALL + GASKET_D + 0.5
    extra = max(0.0, stack_need - (sag + SADDLE_FLAT_T))
    total_h = SADDLE_FLAT_T + sag + extra

    body = oc.rounded_rect(
        f"pod_{side}_saddle",
        (SADDLE_W, SADDLE_L, total_h),
        SADDLE_PLAN_R,
        at=(0.0, 0.0, 0.0),
        anchor="bottom",
        segments=12,
    )
    z_flat_top = total_h
    sag_cut = _concave_neck_cut(body, SADDLE_R, SADDLE_L - 0.5, SADDLE_W - 2.0, z_flat_top)
    rim = oc.rounded_rect(
        "saddle_rim", (SADDLE_W, SADDLE_L, SADDLE_FLAT_T), SADDLE_PLAN_R,
        at=(0.0, 0.0, 0.0), anchor="bottom", segments=10,
    )
    oc.union(body, rim)

    bay_z0 = max(SADDLE_FLAT_T + 0.5, total_h - sag_cut - bh)
    # --- electrode MODULE keep-out ---
    oc.cut(
        body,
        oc.rounded_rect(
            "module_bay", (bw, bl, bh + 1.0), 2.0,
            at=(0.0, module_y, bay_z0), anchor="bottom", segments=8,
        ),
    )
    # --- DRIVER board keep-out (+Y toward cap) ---
    oc.cut(
        body,
        oc.rounded_rect(
            "driver_bay", (dw, dl, dh + 0.5), 2.0,
            at=(0.0, driver_y, bay_z0), anchor="bottom", segments=8,
        ),
    )

    # Gasket seat around combined service opening
    open_w = max(bw, dw) + 2.0 * (BAY_WALL + GASKET_W)
    open_l = span + 2.0 * (BAY_WALL + GASKET_W)
    open_y = 0.5 * (module_y + driver_y)
    g_z = total_h - sag_cut - GASKET_D
    ring_o = oc.rounded_rect(
        "gask_o", (open_w, open_l, GASKET_D), 2.5,
        at=(0.0, open_y, g_z), anchor="bottom",
    )
    ring_i = oc.rounded_rect(
        "gask_i",
        (open_w - 2.0 * GASKET_W, open_l - 2.0 * GASKET_W, GASKET_D + 0.4),
        2.0,
        at=(0.0, open_y, g_z - 0.1),
        anchor="bottom",
    )
    oc.cut(body, oc.cut(ring_o, ring_i))

    # --- Skin-contact lands: BLANK / FLAT only (op-strategy unfitted state) ---
    # No protruding studs, no open electrode holes, no pulse circuit.
    # Internal reserved stud/compliance keep-out stays sealed behind the land
    # face (architect: keep studs in the design as reserved geometry).
    skin_z = total_h - sag_cut
    for i, sy in enumerate((-0.5, 0.5)):
        ey = module_y + sy * ELECTRODE_SPACING
        # Blank/flat skin-contact land (coplanar pad — not a stud)
        land = oc.cylinder(
            f"elec_land_blank{i}",
            ELECTRODE_LAND_D,
            0.6,
            at=(0.0, ey, skin_z - 0.5),
            anchor="bottom",
            segments=24,
        )
        oc.union(body, land)
        if ELECTRODE_STUD_KEEP_OUT:
            # Reserved internal stud well — does NOT pierce the skin land
            oc.cut(
                body,
                oc.cylinder(
                    f"elec_stud_ko{i}",
                    ELECTRODE_D + 0.5,
                    ELECTRODE_COMPLIANCE_TRAVEL,
                    at=(0.0, ey, bay_z0 + bh - ELECTRODE_COMPLIANCE_TRAVEL - 1.0),
                    anchor="bottom",
                    segments=20,
                ),
            )

    # --- Sealed wire path bay → pod face (cell cavity via pod gland @ Y=-28) ---
    module_neg_end = module_y - 0.5 * bl
    wire_z = bay_z0 + WIRE_CH_D * 0.5 + 0.5
    # Strain-relief pocket at module −Y end
    oc.cut(
        body,
        oc.cylinder(
            "wire_strain",
            WIRE_STRAIN_RELIEF_D,
            WIRE_STRAIN_RELIEF_L,
            at=(0.0, module_neg_end - 1.0, wire_z),
            axis="Y",
            segments=20,
        ),
    )
    # Horizontal run module → wire_y
    run_len = abs(module_neg_end - wire_y) + 4.0
    run_mid = 0.5 * (module_neg_end + wire_y)
    oc.cut(
        body,
        oc.cylinder(
            "wire_run",
            WIRE_CH_D,
            run_len,
            at=(0.0, run_mid, wire_z),
            axis="Y",
            segments=20,
        ),
    )
    # Vertical sealed pass-through to flat pod face (mates pod gland)
    oc.cut(
        body,
        oc.cylinder(
            "wire_up",
            WIRE_CH_D,
            bay_z0 + 4.0,
            at=(0.0, wire_y, 0.0),
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
            at=(0.0, wire_y, 0.0),
            anchor="bottom",
            segments=20,
        ),
    )
    # Plug seat on service/neck side of the channel (blank plug when unfitted)
    oc.cut(
        body,
        oc.cylinder(
            "wire_plug_seat",
            WIRE_GLAND_D + 1.0,
            1.5,
            at=(0.0, wire_y, bay_z0 + 0.2),
            anchor="bottom",
            segments=20,
        ),
    )

    # --- Connector position (sense/ID) — reserved pocket in driver bay ---
    cx, cy = CONNECTOR_KEEP_OUT[0], CONNECTOR_KEEP_OUT[1]
    oc.cut(
        body,
        oc.box(
            "connector_ko",
            (cy, cx, CONNECTOR_KEEP_OUT[2] + 0.5),
            at=(dw * 0.25, driver_y, bay_z0 + 0.5),
            anchor="bottom",
        ),
    )
    # --- Hardware kill keep-out — reachable via service lid ---
    oc.cut(
        body,
        oc.box(
            "hw_kill_ko",
            (HW_KILL_KEEP_OUT[1], HW_KILL_KEEP_OUT[0], HW_KILL_KEEP_OUT[2] + 0.5),
            at=(-dw * 0.25, driver_y, bay_z0 + 0.5),
            anchor="bottom",
        ),
    )

    # Service-lid screw clears — land in gasket/wall band around the opening
    screw_span_x = max(COVER_SCREW_SPAN_X, open_w - 2.0 * (BAY_WALL + GASKET_W) - 4.0)
    screw_span_y = max(COVER_SCREW_SPAN_Y, open_l - 2.0 * (BAY_WALL + GASKET_W) - 4.0)
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        oc.cut(
            body,
            oc.cylinder(
                f"cover_h{i}",
                COVER_SCREW_D,
                total_h + 2.0,
                at=(sx * screw_span_x * 0.5,
                    open_y + sy * screw_span_y * 0.5,
                    total_h * 0.5),
                anchor="center",
                segments=16,
            ),
        )

    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
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
    h_out = round(list(oc.size(body))[2], 2)
    meta = {
        "side": side,
        "saddle_R_mm": SADDLE_R,
        "sagitta_mm": round(sag_cut, 2),
        "total_h_mm": h_out,
        "extra_toward_neck_mm": round(extra, 2),
        "height_above_strap_mm": 0.0,
        "review_pod_roof_mm_unchanged": REVIEW_POD_ROOF_MM,
        "layout_y_mm": {
            "module_y": round(module_y, 2),
            "driver_y": round(driver_y, 2),
            "wire_gland_y": wire_y,
            "bay_span": round(span, 2),
        },
        "placeholders": {
            "module": {
                "note": MODULE_NOTE,
                "L_W_H": [MODULE_L, MODULE_W, MODULE_H],
                "margin_xy_z": [MODULE_MARGIN_XY, MODULE_MARGIN_Z],
                "envelope_mm": list(_bay_envelope()),
            },
            "driver": {
                "note": DRIVER_NOTE,
                "L_W_H": [DRIVER_L, DRIVER_W, DRIVER_H],
                "margin_xy_z": [DRIVER_MARGIN_XY, DRIVER_MARGIN_Z],
                "envelope_mm": list(_driver_envelope()),
            },
            "electrode": {
                "note": ELECTRODE_NOTE,
                "D_spacing": [ELECTRODE_D, ELECTRODE_SPACING],
                "skin_land": "blank/flat only",
                "stud_keep_out_internal": ELECTRODE_STUD_KEEP_OUT,
                "unfitted": (
                    "NO electrodes, NO pulse circuit; blank/flat lands; "
                    "studs/pass-throughs reserved + sealed"
                ),
                "compliance_travel_mm": ELECTRODE_COMPLIANCE_TRAVEL,
                "architect_vs_strategy": (
                    "op-architect: keep electrode studs in the design. "
                    "op-strategy: unfitted bay holds no electrodes. "
                    "CAD: blank/flat skin lands + internal sealed stud keep-out. "
                    "Flagged for op-strategy to resolve."
                ),
            },
            "op_architect_reserved": [
                "connector_position",
                "wire_path_with_strain_relief",
                "sealed_pass_through",
                "service_lid_gasket_screws",
                "electrode_stud_keep_out_internal",
            ],
            "unfitted_bay_contents": [
                "service_lid_or_blank_plug",
                "connector_position",
                "wire_path_with_strain_relief",
                "sealed_pass_through",
                "blank_flat_skin_lands",
            ],
            "wire": {
                "note": WIRE_NOTE,
                "conductors_min": WIRE_CONDUCTORS_MIN,
                "channel_d_mm": WIRE_CH_D,
                "gland_y_mm": wire_y,
            },
            "connector_sense_id": {
                "reserved_not_a_design": True,
                "has_sense_id": CONNECTOR_HAS_SENSE_ID,
                "keep_out_LWH": list(CONNECTOR_KEEP_OUT),
                "note": CONNECTOR_NOTE,
            },
            "hw_kill": {
                "reserved_not_a_design": True,
                "keep_out_LWH": list(HW_KILL_KEEP_OUT),
                "note": HW_KILL_NOTE,
            },
            "welfare_tbd": {
                "seal_rules_tbd": SEAL_RULES_TBD,
                "isolation_clearance_tbd_mm": ISOLATION_CLEARANCE_TBD_MM,
                "vent_rules_tbd": VENT_RULES_TBD,
                "note": WELFARE_NOTE,
            },
        },
        "print": {
            "orientation": "flat pod-face on bed; concave neck-face UP; light bowl supports",
            "material": "ASA",
            "brim_mm": 8,
        },
        "design_guardrail": {
            "source": "op-strategy / op-office Halter design-patent comparison",
            "do_not": [
                "narrow low bridge between dominant pods",
                "soft rounded blending",
                "raised ribbed bridge top",
                "vent slots at the pod-bridge joint",
                "glass-look flat pod tops",
            ],
            "keep": [
                "cap dominant",
                "faceted segmented look",
                "blind groove at cap-to-pod joint as a distinct step (no soft blend)",
                "plan corners ≤ R3 (SADDLE_PLAN_R / POD PLAN_R = 3)",
            ],
            "saddle_plan_r_mm": SADDLE_PLAN_R,
            "note": (
                "Pod and saddle changes must not flatten pod tops or add vents "
                "or ribs on the bridge. Earlier fixes must not round corners "
                "beyond the R3 target."
            ),
        },
        "shock_module_interface": (
            "draft PR #30 docs/SHOCK-MODULE-INTERFACE.md — do not edit from this work"
        ),
        "pod_bay_status": (
            "working assumption under Cody Nov 4 stance; placement pending Cody"
        ),
    }
    return body, meta, {
        "open_w": open_w,
        "open_l": open_l,
        "open_y": open_y,
        "wire_y": wire_y,
        "screw_span_x": screw_span_x,
        "screw_span_y": screw_span_y,
    }


def service_lid(side: str = "L", open_w=None, open_l=None,
                screw_span_x=None, screw_span_y=None):
    """Service lid — opens bay without opening cell cavity; seals unfitted bay."""
    bw, bl, _ = _bay_envelope()
    dw, dl, _ = _driver_envelope()
    gw = open_w if open_w else max(bw, dw) + 2.0 * BAY_WALL + 1.0
    gl = open_l if open_l else bl + dl + 6.0
    sx_span = screw_span_x if screw_span_x else COVER_SCREW_SPAN_X
    sy_span = screw_span_y if screw_span_y else COVER_SCREW_SPAN_Y
    cover = oc.rounded_rect(
        f"pod_{side}_bay_cover",
        (gw, gl, COVER_T),
        2.0,
        at=(0.0, 0.0, 0.0),
        anchor="bottom",
        segments=8,
    )
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        oc.cut(
            cover,
            oc.cylinder(
                f"bc_h{i}",
                COVER_SCREW_D,
                COVER_T + 2.0,
                at=(sx * sx_span * 0.5, sy * sy_span * 0.5, -0.5),
                anchor="bottom",
                segments=16,
            ),
        )
    try:
        import build_d5 as d5
        d5.emboss_label(cover, "SERVICE", (0.0, 4.0, COVER_T), rot_z=0.0)
        d5.emboss_label(cover, "BLANK", (0.0, -4.0, COVER_T), rot_z=0.0)
    except Exception:
        pass
    oc.bake(cover)
    oc.move(cover, dz=-oc.bounds(cover)[0][2])
    return cover


def wire_blank_plug(side: str = "L"):
    """Blank plug — seals wire pass-through when bay is unfitted.

    L and R are distinct parts (embossed side letter) — do not share geometry.
    """
    # Stem into channel + flange for seat
    stem = oc.cylinder(
        f"pod_{side}_wire_plug",
        WIRE_CH_D - 0.4,
        6.0,
        at=(0.0, 0.0, 0.0),
        anchor="bottom",
        segments=24,
    )
    flange = oc.cylinder(
        f"wire_plug_flange_{side}",
        WIRE_GLAND_D + 0.5,
        1.5,
        at=(0.0, 0.0, 5.5),
        anchor="bottom",
        segments=24,
    )
    oc.union(stem, flange)
    try:
        # Distinct L vs R glyph on flange top (readable, un-mirrored)
        d5.emboss_glyph(stem, side, (0.0, 0.0, 7.0), size=5.0, depth=0.6)
        d5.emboss_glyph(stem, "ARROW", (0.0, 3.2, 7.0), size=3.5, depth=0.55)
    except Exception as exc:
        print(f"  wire_plug {side} glyph skipped: {exc}")
    oc.bake(stem)
    oc.move(stem, dz=-oc.bounds(stem)[0][2])
    return stem


def _export(obj, path):
    oc.prepare_for_export(obj, merge=1e-4)
    oc.export_stl(obj, path)
    dims = list(oc.size(obj))
    wt = oc.check_stl_watertight(path)
    print(("OK" if wt.get("watertight") else "LOOK"), path, [round(d, 1) for d in dims], wt)
    return dims, wt


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sag_ref = _sagitta(SADDLE_R, 0.5 * SADDLE_L)
    # Height vs review 25 mm lid-top: saddle lives toward neck (below strap).
    # Lid-top above strap is unchanged; extra MODULE/DRIVER depth grows toward neck.
    height_report = {
        "review_pod_lid_top_above_strap_mm": REVIEW_POD_ROOF_MM,
        "holds_25mm_lid_top": True,
        "why": (
            "Saddle + bay stack sits on the neck side of the strap (fills the "
            f"~{sag_ref:.1f} mm flat-underside gap). It does not raise the pod "
            "lid-top above the strap. Print pod stack above strap unchanged."
        ),
        "toward_neck_mm": round(sag_ref, 2),
        "module_vs_sagitta": (
            f"MODULE_H={MODULE_H} (+margins) vs sagitta {sag_ref:.2f}: "
            "any shortfall grows toward neck only, not above strap."
        ),
        "hinge_vs_compliant": (
            "Measured residual vs R208–221 after R220 saddle is ≤0.32 mm. "
            "That does NOT need a hinge. It DOES need compliant/floating "
            "electrode contact (spring or elastomer) when fitted — rigid "
            "curve alone is not skin contact. Hinge reserved only if later "
            "real-neck data shows much larger mismatch."
        ),
    }
    report = {
        "revision": "D8_saddle_complete_bay_keepouts",
        "location_caveat": (
            "Pod bay is a working assumption under Cody's Nov 4 stance "
            "(pilot = production, each pod gets a spot). docs/BOTTOM-BAY.md "
            "and older CAD place pulse elsewhere — neither is final."
        ),
        "unfitted_state": (
            "Service lid + gasket + screws; blank wire plug in sealed "
            "pass-through; blank flat skin-contact lands (no open electrode "
            "holes); connector sense/ID reads not-fitted; no pulse circuit."
        ),
        "op_architect_vs_strategy": (
            "op-architect: keep electrode studs in the design. op-strategy: "
            "unfitted bay holds no electrodes. Resolution: reserved stud "
            "keep-outs with blank/sealed lands when unfitted; open studs "
            "only when fitted. Flagged for op-strategy to confirm."
        ),
        "height": height_report,
        "part_count_delta": {
            "per_pod_was": 2,
            "per_pod_now": 5,
            "added": [
                "pod_*_saddle",
                "pod_*_bay_cover (service lid)",
                "pod_*_wire_plug",
            ],
            "collar_added_qty": 6,
        },
        "bodies": {},
        "pass": True,
    }

    for side in ("L", "R"):
        oc.reset()
        sad, meta, geom = saddle_body(side)
        path = os.path.join(OUT, f"pod_{side}_saddle.stl")
        dims, wt = _export(sad, path)
        report["bodies"][f"pod_{side}_saddle"] = {
            "size_mm": dims, "watertight": wt, **meta,
        }
        if not wt.get("watertight"):
            report["pass"] = False

        oc.reset()
        lid = service_lid(
            side, geom["open_w"], geom["open_l"],
            geom["screw_span_x"], geom["screw_span_y"],
        )
        path = os.path.join(OUT, f"pod_{side}_bay_cover.stl")
        dims, wt = _export(lid, path)
        report["bodies"][f"pod_{side}_bay_cover"] = {
            "size_mm": dims,
            "watertight": wt,
            "role": "service lid — bay openable without cell cavity",
            "print": {"orientation": "flat; label UP", "material": "ASA or PLA"},
        }
        if not wt.get("watertight"):
            report["pass"] = False

        oc.reset()
        plug = wire_blank_plug(side)
        path = os.path.join(OUT, f"pod_{side}_wire_plug.stl")
        dims, wt = _export(plug, path)
        report["bodies"][f"pod_{side}_wire_plug"] = {
            "size_mm": dims,
            "watertight": wt,
            "role": "blank plug — seals wire pass-through when unfitted",
            "print": {"orientation": "flange UP or stem down", "material": "ASA or TPU"},
        }
        if not wt.get("watertight"):
            report["pass"] = False

    with open(os.path.join(OUT, "pod_saddle_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("HEIGHT:", json.dumps(height_report, indent=2))
    print("PASS" if report["pass"] else "FAIL")
    return report


if __name__ == "__main__":
    main()
