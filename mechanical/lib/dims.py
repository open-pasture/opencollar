"""Dimensions of bought parts and printer tolerances, in mm.

Every number says where it came from:
  pub      stated by the manufacturer (datasheet, drawing, board file)
  est      read off a drawing or render; check before relying on it
  measure  not published; measure the real part with calipers
  tune     a printer tolerance; set from the fit_test coupon

Vendor drawings and CAD (nRF9151 STEP, Eagle boards, vent and panel
drawings) are kept locally in reference/vendor/ (not committed); sources are
listed with each part.
"""

# ---------------------------------------------------------------- hardware

# Adafruit 4255, M3 × 4 brass heat-set insert. OD 4.2, length 4 (pub).
# Hole size is tune: fit_test row A sweeps 3.8–4.4.
INSERT_M3 = {
    "od": 4.2,
    "length": 4.0,
    "hole_d": 4.0,       # tune
    "hole_depth": 6.0,   # insert + room for the screw tip
}

# M3 stainless socket-head screws (ISO 4762: head Ø5.5, height 3.0).
M3 = {
    "clear_d": 3.4,           # tune, fit_test row B
    "head_cbore_d": 6.5,
    "head_cbore_depth": 3.2,
}

# 2 mm silicone O-ring cord in a static face seal.
# ERIKS O-ring handbook, table 3.C-1 (pub): depth 1.51 (+0.04/-0), about 24 %
# squeeze; width 2.90 for liquids. Printed values are tune, fit_test row C.
ORING_2MM = {
    "cord_d": 2.0,
    "groove_w": 2.9,
    "groove_d": 1.5,
}

# Amphenol LTW VENT-PS2NGY-O8001 screw-in ePTFE vent, drawing rev D (pub).
# Panel: tapped M6 × 0.75, 45° chamfer to Ø8.6, wall ≥ 4.
# https://amphenolltw.com/product-info/Vent/Vent.M6Plastic/VENT-PS2NGY-O8001.html
VENT_M6 = {
    "thread": "M6x0.75",
    "tap_drill_d": 5.2,       # standard for M6 × 0.75; tune, fit_test row D
    "chamfer_d": 8.6,
    "min_wall": 4.0,
    "hex_af": 10.0,
    "hex_ac": 10.6,
    "length": 12.3,
    "thread_length": 7.0,
}

# ---------------------------------------------------------------- strap

# Heritage Animal Health 48" cow neck strap, double-thick nylon.
# https://www.heritageanimalhealth.shop/products/neck-strap-cow-blue-48-inches
STRAP = {
    "width": 44.45,      # 1-3/4 in (pub)
    "thickness": None,   # measure (not published; guessed 3–4)
    # Designed around until measured. Every strap feature (channel, clamp
    # squeeze, bay tunnel) derives from this, so the real value is one edit.
    "design_thickness": 4.0,  # est
}

# M3 button-head screws (ISO 7380: head Ø5.7, height 1.65) for strap clamp bars.
M3_BUTTON = {"head_cbore_d": 6.5, "head_cbore_depth": 2.0}

# Ballast: mild steel flat bar cut to length, 7.85 g/cm³.
STEEL_SLAB = {"size": (64.0, 46.0, 16.0), "density": 7.85}

# ---------------------------------------------------------------- electronics

# Makerdiary nRF9151 Connect Kit rev A, dimension drawing (pub).
# https://wiki.makerdiary.com/nrf9151-connectkit/hardware/
NRF9151_KIT = {
    "board": (55.88, 20.32, 1.0),
    "above_pcb": 3.26,           # USB-C, tallest top-side part
    "below_pcb": 1.95,           # J2 battery socket
    "hole_d": 1.4,
    "hole_inset": 1.27,          # from each edge, 4 holes
    "usb_c": {"w": 9.0, "overhang": 1.5, "h": 3.26},   # centred on one short end
    "mass_g": 20,
}

# SparkFun MAX-M10S breakout, GPS-18037. Eagle board file (pub).
# https://github.com/sparkfun/SparkFun_u-blox_MAX-M10S
MAX_M10S = {
    "board": (38.10, 30.48, 1.6),
    "holes": [(2.54, 2.54), (35.56, 2.54), (2.54, 27.94), (35.56, 27.94)],
    "hole_d": 3.3,
    "sma_overhang": 6.1,         # right edge, centred at y 15.24
    "height": None,              # measure (SMA is the tallest part)
}

# Adafruit 4755 bq24074 charger. Eagle board file (pub).
# https://github.com/adafruit/Adafruit-BQ24074-PCB
BQ24074 = {
    "board": (38.10, 33.02, 1.6),
    "corner_r": 2.54,
    "holes": [(2.54, 2.54), (2.54, 30.48), (35.56, 2.54), (35.56, 30.48)],
    "hole_d": 2.5,
    "height": None,              # measure
}

# Adafruit 4502 ISM330DHCX, same outline as the LSM6DSOX board (pub).
ISM330 = {
    "board": (25.40, 17.78, 1.6),
    "corner_r": 2.54,
    "holes": [(2.54, 15.24), (22.86, 15.24)],
    "hole_d": 2.5,
}

# SparkFun Qwiic Buzzer BOB-24474 (pub). Buzzer CUI CBT-09427-SMT 9 × 9 × 2.5.
QWIIC_BUZZER = {
    "board": (25.4, 25.4, 1.6),
    "holes": [(2.54, 2.54), (22.86, 2.54), (2.54, 22.86), (22.86, 22.86)],
    "hole_d": 3.3,
    "buzzer": {"size": (9.0, 9.0, 2.5), "at": (12.70, 15.24)},
    "mass_g": 2.85,
}

# Adafruit 353 Li-ion 3.7 V 6600 mAh, 3 × 18650 in parallel (pub).
LIION_6600 = {"size": (69.0, 54.0, 18.0), "mass_g": 155}

# Adafruit 372 10K NTC thermistor body (pub).
THERMISTOR = {"d": 3.3}

# Voltaic P124 1.2 W 6 V ETFE panel (pub). Drawing says 2.8 ± 0.3 thick.
# Solder pads on the back: 4 × 4, 15.5 from a short edge, first pad 26 from
# the left, 6 pitch. Mounted with a VHB gasket.
# https://voltaicsystems.com/content/P124_ds.pdf
P124_PANEL = {"size": (113.0, 66.0, 3.1), "mass_g": 31.6}

# "1575R-A" 25 × 25 ceramic GPS patch on U.FL.
GPS_PATCH = {
    "ceramic": (25.0, 25.0, 4.0),  # vendor listings only
    "height": None,                # measure (patch + LNA board + shield)
}

# LTE flex antenna supplied with the Connect Kit.
LTE_FLEX = {"size": None}          # measure (about 44 × 10 from a render, est)
