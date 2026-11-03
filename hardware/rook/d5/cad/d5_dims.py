"""D5 production dimensions and assumptions.

Sources: HARDWARE-FIT.md, dims.py, op-firmware enclosure-component-spec
(headline dims), op-brand D5 conditions, D5 look-study package.

V = verified from datasheet/drawing. U = unverified / assumed / tune.
"""

# ---------------------------------------------------------------- strap (U until calipers)
STRAP_W = 44.45          # V — 1-3/4 in pub
STRAP_T = 4.0            # U — design_thickness; VERIFY WITH CALIPERS
STRAP_R = 232.0          # U — look-study collar radius (mm); form reference

# Brand: cap width ≤ ~1.3 × strap → 57.8 mm. CONFLICT with P124 (66 mm panel).
# With P124 pocket (OPEN Cody/strategy) cap stays 76. If panel dropped → CAP_W_SLIM.
CAP_W_MAX_BRAND = round(STRAP_W * 1.3, 1)  # 57.8
CAP_W_SLIM = 58.0                       # brand target when P124 dropped

# ---------------------------------------------------------------- locked / production envelope
CAP_W, CAP_L = 76.0, 160.0          # V — P124-sized footprint (OPEN panel decision)
CAP_WALL = 5.0
CAP_FLOOR = 6.0
# Internal free height ≈ CAP_CAVITY_H + lid underside (~1.3) ≈ 14.3 mm.
# UPRIGHT Wio 23 mm and kit+headers ~17 mm DO NOT FIT — see FIT_HEIGHT_NOTE / Cody.
CAP_CAVITY_H = 13.0                 # fitted for low-profile kit (7.2) + lay-flat Wio
CAP_BASE_H = CAP_FLOOR + CAP_CAVITY_H  # 19
CAP_LID_T = 6.5
CAP_STACK_H = CAP_BASE_H + CAP_LID_T  # 25.5 total
# Taper zone shortened so central cavity stays full for kit + bq.
CAP_TAPER_LEN = 14.0                # outer tip only; cavity flat for |y| < L/2 - TAPER
# Columns at y=-42 moved outboard (x=±31.5) so Ø8 bosses clear kit pocket corner.
CAP_COLS = [(sx * 29.5, y) for sx in (-1, 1) for y in (-68.0, 42.0, 68.0)] + \
           [(sx * 31.5, -42.0) for sx in (-1, 1)]
CAP_CLAMP = [(sx * 20.0, sy * 28.5) for sx in (-1, 1) for sy in (-1, 1)]
# Orange = farmer service: 3 end screws clear of centered P124 (±56.8).
CAP_ORANGE = [(29.5, 68.0), (-29.5, 68.0), (29.5, -68.0)]
CAP_CHARCOAL = [c for c in CAP_COLS if c not in CAP_ORANGE]

# Brand: pods visibly LOWER than cap. Tight 1781 cradle + thin lid.
# Cell Ø19.2 needs ~cav 19.5; floor 2.5 + cav 19.5 + lid 3.0 = 25.0 < cap 25.5.
POD_CAVITY = (82.0, 58.0, 19.5)
POD_WALL = 5.0
POD_L = POD_CAVITY[0] + 2 * POD_WALL  # 92
POD_W = POD_CAVITY[1] + 2 * POD_WALL  # 68
POD_FLOOR = 2.5
POD_BASE_H = POD_FLOOR + POD_CAVITY[2]  # 22.0
POD_LID_T = 3.0
POD_STACK_H = POD_BASE_H + POD_LID_T    # 25.0 — visibly under cap 25.5
POD_COLS = [(sx * 37.0, sy * 27.0) for sx in (-1, 1) for sy in (-1, 1)]
# Pods sit ~±80 mm along strap from spine (look-study).
POD_STRAP_Y = 80.0

CW_L, CW_W, CW_H = 88.0, 74.0, 30.0  # steel pack; no electronics
CW_LID_T = 6.0
CW_SCREWS = [(sx * 22.0, sy * 31.5) for sx in (-1, 1) for sy in (-1, 1)]
CW_CLAMP = [(sx * 36.0, sy * 29.5) for sx in (-1, 1) for sy in (-1, 1)]

# Seam family (op-brand): shared height fraction, 0.5 mm inset reveal.
WAIST_FRAC = CAP_BASE_H / (CAP_BASE_H + CAP_LID_T)
REVEAL = 0.5
PLAN_R = 7.0
CROWN_R = 2.5                       # look; print as clean flat + soft plan (no dust ledge)
GROOVE_W, GROOVE_D = 2.6, 1.5       # 2 mm cord
MIN_LAND = 1.5

# Saddle — wider than look-study to stop ~58 mm overhang rock each side.
SADDLE_W = CAP_W
SADDLE_L = 96.0                     # covers clamp ±28.5 + overhang support
SADDLE_H = 2.5 + (STRAP_T - 0.6)    # roof + channel
SADDLE_CHANNEL_W = STRAP_W + 2.0
SADDLE_CHANNEL_D = STRAP_T - 0.6

# Fairings (op-brand): 25–30 mm run into strap, R7 plan + R2.5 soft edges.
FAIRING_RUN = 28.0                  # within 25–30 mm brand blend
FAIRING_R = PLAN_R                  # 7.0 plan radius
FAIRING_EDGE_R = CROWN_R            # 2.5 soft edge bevel

# P124 — OPEN DECISION (Cody/strategy). Pocket kept; flag in PR.
PANEL_POCKET = (66.6, 113.6, 2.3)
PANEL_SIZE = (66.0, 113.0, 2.6)
PANEL_Y = 0.0                       # centered; GPS patch takes −Y cavity end if panel confirmed
PANEL_OPEN_DECISION = True

# Label (op-brand)
LABEL = (30.0, 12.0, 0.5)
LABEL_TEXT = "ROOK-001"
LABEL_SIZE = 6.0

# Fasteners
CLEAR = 3.4
INSERT_D = 4.0
CBORE_D = 6.5
PLUG_SEAT_D, PLUG_SEAT_H = 8.2, 1.35
PLUG_D, PLUG_H = 8.0, 1.25

# ---------------------------------------------------------------- component pockets (board + 0.4/side)
# Policy: pocket = board + 2×BOARD_CLEAR on XY; height from spec or U.
BOARD_CLEAR = 0.4                   # per side (adjustable — fit coupon sweeps)

def pocket_xy(board_xy, clear=BOARD_CLEAR):
    return (round(board_xy[0] + 2 * clear, 2), round(board_xy[1] + 2 * clear, 2))


# Rook Connect Kit (V outline; height U with headers)
# PCB 55.88 × 20.32 × 1.0; USB-C +3.26 side; battery JST +1.95 underside.
# 4 holes dia 1.4 inset 1.27; USB-C centered on a short end; LTE/GNSS U.FL
# at antenna end; nano-SIM slot. Lives in CAP (+ pods cable runs). CW free.
KIT_BOARD = (55.88, 20.32, 1.0)     # V
KIT_HOLE_D = 1.4                    # V
KIT_HOLE_INSET = 1.27               # V from each edge
KIT_USB_H = 3.26                    # V side protrusion
KIT_JST_H = 1.95                    # V underside
KIT_POCKET_XY = pocket_xy(KIT_BOARD)  # 56.68 × 21.12 → use headline 56.7 × 21.1
KIT_POCKET = (56.7, 21.1, 7.2)      # V headline; LOW-PROFILE (no headers) — FITS 13 mm cavity
KIT_POCKET_HEADERS = (56.7, 21.1, 17.0)  # U ~17 with socketed headers — DOES NOT FIT (Cody)
KIT_AT = (0.0, -24.0)               # −Y; shifted +4 from −28 to clear column at y=−42

# bq24074 Adafruit 4755 — V outline; do NOT pot charger solid
BQ_BOARD = (38.10, 33.02, 1.6)      # V
BQ_HOLE_D = 2.5                     # V
BQ_HOLE_INSET = 2.54                # V
BQ_POCKET = (38.9, 33.8, 12.0)      # V headline (= board + 0.4/side); fits under 13 mm cav
BQ_AT = (0.0, 28.0)                 # +Y; moved from 22 to clear U.FL channel at +X wall

# Qwiic buzzer SparkFun BOB-24474 — open sound port + mesh
BUZZ_BOARD = (25.4, 25.4, 1.6)      # V
BUZZ_POCKET = (26.2, 26.2, 8.0)     # V headline
BUZZ_PORT_D = 8.0
BUZZ_MESH_PITCH = 1.6               # print-in mesh bars across port
BUZZ_MESH_BAR = 0.6
BUZZ_AT = (18.0, 12.0)              # per HARDWARE-FIT pod layout

# Protected 18650 Adafruit 1781 (V). Adafruit 353 pack NOT approved.
# Flat LiPo LP503562 ~5×35×62 U — cell bay adjustable.
CELL_D, CELL_L = 18.4, 69.0         # V
CELL_POCKET_D = 19.2                # V headline
CELL_POCKET_L = 70.0                # V headline
CELL_END_CLEAR = 3.0                # ~3 mm each end for springs/leads
CELL_BAY_L = CELL_POCKET_L + 2 * CELL_END_CLEAR  # 76
# Radial spare limited so Ø ≤ pod cavity height 19.5 (brand: pods lower than cap).
CELL_BAY_ADJUST = 0.2               # Ø19.4 in 19.5 cav; LP503562 still notes U
CELL_AT = (-2.0, -8.0)              # pod cradle centre (X along cell)

# Wio-SX1262 — ~21 × 17.8; height U (21–23 upright). Cap cavity ~14.3 free —
# UPRIGHT DOES NOT FIT. Production option: LAY-FLAT pocket (board in XY).
WIO_BOARD = (21.0, 17.8)            # U
WIO_POCKET_UPRIGHT = (21.8, 18.6, 23.0)  # headline; DOES NOT FIT current cavity
WIO_POCKET = (21.8, 18.6, 8.0)      # LAY-FLAT option (board + connectors U) — FITS
WIO_WIRE_BEND = 20.0                # U.FL / SMA slack along +X wall (not over bq)
WIO_AT = (26.0, -8.0)               # +X wall, clear of bq (+Y) and kit (−Y)
WIO_ORIENTATION = "lay_flat"        # production default until Cody raises cavity

# Starling: XIAO nRF52840 + Wio stack — same XY pocket, SMALL CELLS ONLY
STARLING_POCKET = (21.8, 18.6, 25.0)
STARLING_NOTE = (
    "Starling shares Wio XY pocket 21.8×18.6; stack height U. "
    "Small cells only — no 18650 dual-pod plan. Separate CAD TBD."
)

# Antennas — crest side, away from neck and cells.
# Keep metal inserts, screws, steel CW, cells 10–15 mm from antennas.
GNSS_PATCH = (25.0, 25.0, 4.0)      # ceramic; sky-facing under 1–3 mm plastic, no metal above
GNSS_COVER_T = 2.0                  # plastic over patch (1–3 mm)
LTE_FLEX = (44.0, 10.0, 0.8)        # U flex footprint
LORA_915 = "U.FL or SMA"            # crest; not toward neck
ANTENNA_METAL_KEEP = 12.0           # mid of 10–15 mm keepout
# Cap crest = +Y lid / outer (sky). GNSS shelf under lid at +Y free of P124 if panel −Y.
GNSS_AT = (0.0, 55.0)               # crest; ≥ keepout from columns at y=±68,±42
LTE_AT = (0.0, 40.0)                # crest flex shelf

# USB-C charge port + gasket cap; light pipe; button membranes; U.FL strain
USBC_PORT = (10.0, 8.0, 6.0)
USBC_CAP = (12.0, 10.0, 3.0)
LIGHTPIPE_D = 2.5                   # over kit / charger LEDs
BTN_MEMBRANE = (8.0, 8.0, 1.2)      # press-through TPU over buttons
UFL_STRAIN_D = 3.5                  # cable strain relief boss ID
UFL_SLACK = 20.0                    # mm free length before clamp

# Fit coupon clearances to sweep (print FIRST)
COUPON_CLEAR_SWEEP = (0.2, 0.4, 0.6)  # per-side board clear options

# Printer beds
BED_P2S = (256.0, 256.0, 256.0)
BED_220 = (220.0, 220.0, 250.0)     # Ender-class
BED_MK4 = (250.0, 210.0, 220.0)

# Cap free height vs radio/kit — DO NOT GUESS a raised cavity; Cody decides.
FIT_HEIGHT_NOTE = (
    "Cap free height ≈ 14.3 mm (13 cavity + ~1.3 lid recess). "
    "Wio-SX1262 upright pocket needs ~23 mm + 20 mm wire bend — DOES NOT FIT. "
    "Connect Kit with socketed headers needs ~17 mm — DOES NOT FIT. "
    "Production CAD uses LAY-FLAT Wio (8 mm pocket) + LOW-PROFILE kit without "
    "headers (7.2 mm). Alternatives for Cody: (A) keep lay-flat/low-profile, "
    "(B) raise cap cavity ≥23 mm (hurts brand proportions / pod-lower look), "
    "(C) solder headers / remote radio. Flagged OPEN for Cody."
)

ASSUMPTIONS = [
    "Strap thickness 4.0 mm assumed — VERIFY WITH CALIPERS before field print.",
    "P124 on cap is an OPEN Cody/strategy decision; pocket retained for study.",
    "Cap 76 mm exceeds brand 1.3× strap (~57.8 mm) while P124 is in play; CAP_W_SLIM=58 if panel dropped.",
    "bq24074 / GPS patch heights partially assumed — verify with calipers.",
    FIT_HEIGHT_NOTE,
    "Wio production orientation = lay_flat until Cody raises cavity for upright.",
    "LP503562 LiPo unverified (~5×35×62); cell bay has +1 mm radial adjust (pod height).",
    "Adafruit 353 pack is NOT approved; dual 1781 pods are plan of record.",
    "Rook Connect Kit fitted LOW-PROFILE 7.2 (no headers); ~17 with sockets DOES NOT FIT.",
    "LTE flex 44×10 U; GNSS cover 1–3 mm plastic, no metal above patch.",
    "Antenna metal keepout 10–15 mm (CAD uses 12 mm) from inserts/screws/CW/cells.",
    "Do not pot the bq24074 charger solid — service access required.",
    "Cell swap needs only an M3 driver (pod lid orange/service screws).",
    "Counterweight tub stays free of electronics — steel pack only.",
    "Pods stack 25.0 mm < cap stack 25.5 mm (brand: pods visibly lower).",
    "Starling: same Wio XY pocket; small cells only; separate CAD TBD.",
    "No collar on animal until welfare review (PR #2).",
    "Parts arriving Nov 4–6 — pockets +0.4 mm/side; fit coupon FIRST.",
]

CODY_FLAGS = [
    "FIT HEIGHT: upright Wio 23 mm + kit headers 17 mm vs ~14.3 mm free — choose A/B/C in FIT_HEIGHT_NOTE.",
    "P124 panel OPEN — keep cap 76 or drop panel and take CAP_W_SLIM 58 (brand 1.3× strap).",
    "Mono vs stereo buzzer; 1781 purchase (HARDWARE-FIT).",
]

# Layout rule (firmware): Rook pockets in CAP and PODS; CW no electronics.
LAYOUT = {
    "cap": ["Rook Connect Kit", "bq24074", "Wio-SX1262", "GNSS patch", "LTE flex",
            "915 LoRa U.FL/SMA", "USB-C + gasket cap", "light pipes", "button membranes"],
    "pod_L": ["18650 1781", "Qwiic buzzer + mesh port", "cable to cap"],
    "pod_R": ["18650 1781", "Qwiic buzzer + mesh port", "cable to cap"],
    "cw": ["steel counterweight only — NO electronics / antennas"],
    "starling": STARLING_NOTE,
}
