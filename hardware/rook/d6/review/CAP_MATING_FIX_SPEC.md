# Cap mating fix — exact CloudAgent spec (draft PR #28)

**For:** CloudAgent `bc-d1b3bd14-9f90-5362-8b3c-de88ecfc1b5c`  
**Repo:** `open-pasture/opencollar` draft PR #28  
**Do not merge. Keep draft.**  
**Proven in:** `/tmp/cap_mating_proto/` (0.00 mm³ overlap, 0.00 mm land seam, XY clear 0.280/0.280, Z clear 0.40)

Cody: *"Take your time and have it fixed properly."*

---

## Root causes confirmed on `7fdaf2f` STLs

1. **`end_taper_d4` / `end_nose_contoured` chops the parting deck** for `|Y| > ~50`, so `cap_lid`'s flat underside (z_stl=33) hangs over curved noses (gap up to 12.9 mm). Plan radius also mismatched (`PLAN_R=3` body vs `NOSE_PLAN_R=14` tips; lid used `PLAN_R-0.5=2.5`).
2. **`CAP_COLS_POKA` took the first 4 of D5's 8 `CAP_COLS`**, which includes `(-29.5, +43.05)` — **inside the 67.2×114.2 P124 pocket**. Once VHB-glues the solar panel, that screw is trapped forever. The 3 nose screws at `|Y|=69.7` were then deleted by `end_taper_d4` (no bosses).
3. **`d5.reg_lip` vs hardcoded `lring`** collide by 0.60 mm (`144 mm³` Boolean overlap → 1.20 mm seam ride-up). Lip only spans `|Y|≤50`; no Y registration.

## Critical hardware discoveries

### A. `CAP_COLS` / P124 (MUST FIX)
D5 `CAP_COLS` = 8 structural columns including mid-body `Y=±42` (scaled → `43.05`). D5 `CAP_ORANGE` (farmer service) was already the 3 end screws clear of P124.  
**Production rule:** all 4 lid screws MUST sit outside `PANEL_POCKET` (`|Y| ≥ 57.1 + CBORE_R ≈ 60.4`) so the lid can be removed after P124 is VHB-glued.

**Locked `CAP_COLS` (replace `CAP_COLS_POKA` block):**
```python
CAP_COLS = [
    (-29.5,  69.70),  # +Y −X
    ( 29.5,  69.70),  # +Y +X
    (-26.5, -69.70),  # −Y −X  poka-yoke (+3 X from −29.5)
    ( 29.5, -69.70),  # −Y +X
]
```
- 180° rotation misses (poka verified).
- Optional: add a small asymmetric key bump in the rabbet at e.g. `(+33.0, +40)` / matching notch in lid groove so the lid cannot even drop into the rabbet backwards.

### B. USB-C axis (KEEP −Y; notch the pad)
makerdiary nRF9151 Connect Kit is `55.88 × 20.32` with USB-C on a **short edge**. With `KIT_BOARD=(55.88, 20.32)` at `KIT_AT=(0,−24)`, the short edges face `±Y` → USB faces **−Y**. D5 comment `USB→−Y` is correct; do **not** rotate the kit to ±X.

**Problem:** `pod_mount_pad("L")` is `36×4×14` centered on `X=0` at `y≈−88.3`, fully blocking the USB tunnel exit (`X∈[−18,+18]` solid at `y=−86,z=24`).

**Fix:** cut a **U-notch / cable arch** through `pod_mount_pad("L")` (and verify `"R"` has no USB — only L/−Y needs it):
```python
PAD_USB_NOTCH_W = 12.5   # clears USBC_PORT 10.5 + overmold; ≥2.0 mm plastic to M3 hole edge at lx=±10
PAD_USB_NOTCH_H = 12.0   # covers usbc_z band through pad height
# In pod_mount_pad("L"): after screw holes, before tilt/place:
oc.cut(pad, oc.box("usb_notch", (PAD_USB_NOTCH_W, pt + 4.0, PAD_USB_NOTCH_H),
                   at=(0.0, 0.0, /* USB local-Z band center relative to pad */),
                   anchor="center"))
```
Screws stay at `POD_MOUNT_SCREWS = [(±10, 3), (±10, 10)]`. Notch edge at `±6.25`; M3 hole edge at `10−1.7=8.3` → **2.05 mm** wall.

### C. `cap_usbc_plug` clearance
Target **0.20–0.25 mm/side**. Current stem `ux−0.6` → 0.30/side (slightly loose). Change to:
```python
USBC_PLUG_CLEAR = 0.22
stem = oc.rounded_rect(..., (ux - 2*USBC_PLUG_CLEAR, 8.0, uz - 2*USBC_PLUG_CLEAR), ...)
```

### D. SMA vs parting deck
Hex nut seat AF=10 at `CAP_FLOOR+6=12` → corner top ≈17.77, only 1.23 mm below `CAP_BASE_H=19`.  
**Lower SMA center to `CAP_FLOOR + 5.2 = 11.2`** (corner top ≈16.97 → **2.03 mm** below parting). Keep `Ø6.6` bulkhead + `10` AF seat.

### E. Lid support posts
Already top at `CAP_BASE_H − 0.4` in `7fdaf2f` — keep `≥0.35 mm` recess. Do **not** let posts or boss tops reach the parting plane.

---

## Geometry lock (production)

| Param | Value | Notes |
|---|---|---|
| `CAP_W × CAP_L` | `76 × 164` | unchanged |
| `CAP_BASE_H` | **`19.0`** | keep; `LID_H=12`, `CAP_STACK_H=31` |
| `R_BASE` (`NOSE_PLAN_R`) | **`14.0`** | **entire** stadium plan (replace `PLAN_R=3` on cap slab) |
| `R_LID` | **`13.5`** | `R_BASE − REVEAL` |
| Lid plan | `75 × 163` | uniform 0.50 reveal on ±X, ±Y, **and corners** |
| Parting | **continuous planar** `z=CAP_BASE_H` under full lid footprint | **delete** `end_taper_d4` cut of the deck |
| Base nose | exterior-only chin/bevel **below** parting if desired; deck untouched | full wall height at ends → bosses live |
| Lid nose | keep `end_crown_taper` + `crown_shoulders` **above** `z=0` | mating face stays flat on bed |
| Outer land | `1.80` mm wide | lid inset `0..1.80` |
| Lid groove | inset `1.52..3.48` (`w=1.96`), depth `1.60` | |
| Base tongue | lid-equiv inset `1.80..3.20` (`w=1.40`), height `1.20` | |
| XY clear | **`0.28` mm/wall** both sides | in band 0.25–0.30 |
| Z clear | **`0.40` mm`** | ≥0.35 so land seats first, 0.00 overlap |
| Boss | `Ø8.0`, insert `Ø4.0 × 6.0` deep, top recess `0.40` below parting | |
| Lid cbore | `Ø6.4 × 2.8` deep, contour-aware | ≥3.0 mm clamp meat; at `Y=±69.7` local top ≈7.93 → meat ≈5.13 |

**Rabbet construction (concentric stadium rings, replace `d5.groove` + `d5.reg_lip` + lid `lring`):**
```python
# lid mating face (z=0):
groove = ring_stadium(
    out=(LW - 2*1.52, LL - 2*1.52, R_LID - 1.52),   # 71.96 × 159.96, R=11.98
    inn=(LW - 2*3.48, LL - 2*3.48, R_LID - 3.48),   # 68.04 × 156.04, R=10.02
    h=1.60, z0=0.0)
oc.cut(lid, groove)

# base parting deck (z=CAP_BASE_H):
tongue = ring_stadium(
    out=(LW - 2*1.80, LL - 2*1.80, R_LID - 1.80),   # 71.40 × 159.40, R=11.70
    inn=(LW - 2*3.20, LL - 2*3.20, R_LID - 3.20),   # 68.60 × 156.60, R=10.30
    h=1.20, z0=CAP_BASE_H)
oc.union(base, tongue)
```
Optional inner O-ring groove deferred (tongue-and-groove is the weather seal).

**Contour-aware lid fasteners** (after `end_crown_taper`):
```python
PAD_Z = 7.5   # flat local pad top; ≥ CBORE_DEPTH + MIN_CLAMP = 5.8
for i,(x,y) in enumerate(CAP_COLS):
    oc.union(lid, oc.cylinder(f"spad{i}", 10.0, PAD_Z, at=(x,y,0), anchor="bottom"))
    oc.cut(lid, oc.cylinder(f"h{i}", CLEAR, LID_H+2, at=(x,y,-1), anchor="bottom"))
    oc.cut(lid, oc.cylinder(f"cb{i}", 6.4, 2.8, at=(x,y, PAD_Z-2.8), anchor="bottom"))
```

**`cap_base` slab:** use `R_BASE=14` (not `PLAN_R=3`):
```python
b = slab("cap_base", CAP_W, CAP_L, CAP_BASE_H, R_BASE)
# REMOVE: end_taper_d4(b, ...)   # do not chop the deck
# KEEP: skirts, pod pads (with U-notch on L), pockets, SMA (lowered), USB tunnel
```

**`cap_lid` slab:**
```python
lid = slab("cap_lid", LW, LL, LID_H, R_LID)
# REMOVE: old lring cut
# ADD: 360° groove as above
# KEEP: crown_shoulders, end_crown_taper, P124 pocket, LTE, lightpipe/btn wells, wrap step
# REPLACE: d5.lid_fasteners → contour-aware pads+cbore on CAP_COLS
```

---

## Keep intact (6 hardware clearances from `7fdaf2f`)

1. P124 pocket `67.2 × 114.2 × 3.1` (`≥2.0` lid under, `Ø4.5` wire hole)
2. nRF9151 ribs `57.6 × 21.4` + `2.8` J2 recess + cleared PCB floor
3. SMA `Ø6.6` + `10` AF hex seat (center lowered to `CAP_FLOOR+5.2`)
4. −Y USB-C tunnel + `cap_usbc_plug` at `0.22` mm/side
5. D7r19 grooves / `001` glyphs
6. D5 embossed L/R/arrows + asymmetric keyed lid bosses (via poka `CAP_COLS`)

---

## Verification (mandatory before waking CoS)

```bash
python3 audit/verify_cap_mating_and_plot.py \
  --stl-dir hardware/rook/d8/stl \   # or wherever STLs land
  --out-dir audit/
# Expect: all gates PASS, writes cap_lid_mating_verified.png + .json
```

Also:
1. Re-slice PLA cap plate (`OrcaSlicer` + `fix_bbl_3mf.py`) — report margin & time.
2. Generate plate `.blend` AND assembled+exploded `.blend` with `VIEW_3D` `clip_end=10000`, `OBJECT` color + cavity, framed on geometry. Match object naming spirit of `d8_x2a_7fdaf2f_assembled_review.blend` (`A_cap_base`, `A_cap_lid_seated_z33`, `E_*` exploded).
3. Do **NOT** copy to Mac / touch Bambu Connect.
4. Reply to CoS with new commit SHA, slice stats, box paths; `priority: true`.

---

## Proto proof paths (this box)

- `/tmp/cap_mating_proto/proto_cap_base_mating.stl`
- `/tmp/cap_mating_proto/proto_cap_lid_mating.stl`
- `/tmp/cap_mating_proto/proto_verify.json`
- `/workspace/opencollar/stage-2026-11-05-sprint-fri/audit/verify_cap_mating_and_plot.py`
- `/workspace/opencollar/stage-2026-11-05-sprint-fri/audit/CAP_MATING_FIX_SPEC.md` (this file)
- Baseline fail on `7fdaf2f`: `/tmp/cap_mating_proto/baseline_7fdaf2f/`
