# Node V1 hardware fit audit (2026-11-02)

## Bottom line
**Yes, the solar pocket is a mistake.** The Node V1 cap was drawn for **2 × Voltaic P122 (52 × 52 mm, 5 V, 0.3 W)**, a panel that was never bought. Cody bought **2 × Voltaic P124 (113 × 66 mm, 1.2 W)**. The P124 is 2.2× the pocket length and 4 mm wider than the whole 62 mm cap, which is exactly what Cody saw.

**Recommendation: don't buy new panels. Resize the cap to take ONE of the P124s you already own** (cap about 76 × 160 mm, pocket 113.6 × 66.6 × 1.2). One P124 (1.22 W peak) gives about 2× the power of the two P122s the CAD assumed (0.6 W total). Its 6 V class output also suits the bq24074, which the cart notes say wants 6–10 V solar input; the P122 is a 5 V class panel. The second P124 is a spare.

**Second mistake, also blocking:** the pods are drawn for 2 × Adafruit 1781 18650 cells (one per pod), but none were bought. What was bought is 1 × Adafruit 353 6600 mAh pack (69 × 54 × 18), which does not fit a pod. **Cheapest fix: buy 2 × Adafruit 1781 ($9.95 each, in stock).** Cody approves that purchase.

## Where each assumption came from
- `mechanical/lib/node_v1.py` lines 7 and 56: "2 x Voltaic P122 panels on the lid", `P122 = {"size": (52.0, 52.0, 3.0)}`. Lines 74–75: `PANEL_Y = (-12.3, 41.7)`, `PANEL_POCKET = (52.6, 52.6, 1.2)`. Line 64: `CAP_W, CAP_L = 62.0, 142.0`. The docstring says unit #1 is built "from parts already on hand", but the P122 was never on hand.
- The repo's own `mechanical/lib/dims.py` has `P124_PANEL = (113.0, 66.0, 3.1)`. `hardware/prototype-cart.md` and `hardware/orders-2026-09-26.md` list Voltaic order 100066117: 2 × P124, $28.00 + $13.57 shipping. BUILD-LOG lines 73 and 99 note that two P124s make the top unit much wider. So the node_v1 rewrite swapped in a smaller panel without anyone ordering it.
- Line 55: `CELL` = Adafruit 1781 (18.4 × 69). It isn't in any order. The Adafruit packing slip (BUILD-LOG line 368) has the 353 pack, not the 1781.

## Every bought part vs the CAD
| Part (as bought) | Source | Bought dims | CAD assumes | Verdict |
|---|---|---|---|---|
| Solar: Voltaic P124 ×2 | Voltaic order 100066117 (repo); Adafruit 5368 page | 113 × 66 × 2.6 (2.8±0.3 per Voltaic drawing), 1.22 W, Voc 7.09 V | P122 52 × 52 × 3 pocket 52.6 × 52.6 × 1.2, ×2; cap 62 wide | **MISMATCH, doesn't fit** |
| Battery: Adafruit 353 3.7 V 6600 mAh (3×18650) | Adafruit 3751847 slip | 69 × 54 × 18, 155 g | 1 × 1781 cell per pod, pod cavity 82 × 58 × 21.5 with Ø8 corner columns at (±37, ±27) and buzzer at x = 20 | **MISMATCH.** The pack's corners hit the columns (needs x ≤ 33 where y > 23) and it sits on the buzzer. Only one pack for two pods. |
| Battery: PKCELL LP503562 1200 mAh LiPo | bom.md (owned) | ~50 × 35 × 5.6 (nominal from model code, *inferred*) | not used in node V1 | Not in the design (bench only) |
| Board: Makerdiary nRF9151 Connect Kit | Gmail: makerdiary #MS3066, 2026-09-14 CT, $58.00 | 55.88 × 20.32 × 1.0, +3.26 above / 1.95 below (pub) | Same (`dims.NRF9151_KIT`), in a 52 × 132 × 13 cap cavity | OK |
| Charger: Adafruit 4755 bq24074 | Adafruit slip | 38.10 × 33.02 board; height not published | Same; height 11 *est* | OK in plan; **measure the height** (cavity is 13) |
| IMU: Adafruit 4502 ISM330DHCX | Adafruit slip | 25.4 × 17.78 | Same | OK |
| GPS patch 1575R-A 25 × 25 U.FL | bom.md (owned) | 25 × 25 × 4 ceramic (listing) | 25 × 25 × 6 *est* under the lid | OK in plan; measure the height |
| LTE flex antenna (kit) | bom.md | not published | 44 × 10 *est* on the cavity wall | Measure |
| SparkFun MAX-M10S + Adafruit 960 antenna | DigiKey SO 101875374 / Adafruit | 38.1 × 30.48 + SMA | **not in node V1** | Bench only; fine |
| Qwiic Buzzer BOB-24474 | bom.md (owned, **1**) | 25.4 × 25.4 | 1 per pod = **2 needed** | **Short 1.** BUILD-LOG line 152 says a second one isn't ordered. |
| Heat-set inserts Adafruit 4255 M3 × 4, 50 pcs | Adafruit slip | OD 4.2, L 4 | hole 4.0 (tune), 12 cap + 16 pod + 8 cw = 36 | OK (50 ≥ 36) |
| M3 screws: Amazon B0GHMM79M9 "M3 304 stainless assortment" | Amazon 112-4704164-9521866 | Contents not verified (Amazon blocked the fetch) | 8 × M3×20 + 8 × M3×25 button head, M3×8/×6, bonded M3 sealing washers ×16, 2 × M4×10 pan + nut + O-ring | **Unverified.** Assortments usually stop at 20 mm, so M3×25, sealing washers and M4 are likely missing. |
| 2 mm O-ring cord, Amazon B00QVB0ZG6 | Amazon 112-2245515-4903446 | 2 mm | groove 2.9 × 1.5 | OK |
| Strap: Heritage 48" 1-3/4" | Heritage 20266 | 44.45 wide; thickness not published | 44.45, 4.0 *est* | Measure the thickness |
| Steel 2 × 1/4 flat bar, 4 × 3 in | not bought online | 76.2 × 50.8 × 6.35 | cw tub 88 × 74 × 30 | Buy locally / confirm |

## Options for the panel
| Option | Panel | Size (mm) | Power | Price (verified on page today) | Cap change |
|---|---|---|---|---|---|
| **A (recommended)** | 1 × P124, **already owned** | 113 × 66 × 2.6 | 1.22 W, 6.07 V peak | $0 | Cap to ~76 × 160; one pocket 113.6 × 66.6 × 1.2; GPS patch moves to the free end |
| B | 2 × Voltaic P123 | 66 × 66 × 2.6 | 0.71 W each, 6.23 V peak, Voc 7.28 | $9.00 each, https://voltaicsystems.com/0-6-watt-6-volt-solar-panel-etfe/ | Cap to ~76 × ~175 (two pockets + patch); longest option |
| C | 2 × Voltaic P122 (what the CAD drew) | 52 × 52 × 3 | 0.3 W each, 5 V class | $5.95 each, https://www.adafruit.com/product/5855 (in stock) | None, but lowest power and a 5 V panel on a charger the notes rate for 6–10 V input |

Knock-on effects of option A (*estimates*): the cap plan area grows ~1.38×, so the cap goes from ~3h32m to ~4h50m on the current PLA fit profile. A 76 × 160 cap fits the 256 × 256 P2S plate easily, though 2 caps per plate gets tight. The strap channel, clamp bars (70 long) and spine relief keep their size; only the lid/base outline, the column positions (x ±29.5) and the clamp-bar insert spacing stay or grow. The cap is 14 mm wider over the neck crest. Mass +~20 g from the bigger panel (31.6 vs 2 × 12.1 g) plus plastic.

The repo doesn't document a power need for node V1. The BUILD-LOG target is ~60 days at ~20 Wh with a big counterweight battery, which isn't this unit. **Assumption:** unit #1 is a bench and field prototype, so more panel power is better and option A is strictly better than C.

## Ask Cody (fastest checks)
1. Photo of the panels' backs or labels to confirm they're P124s (113 × 66).
2. Calipers: strap thickness, bq24074 board tallest part, GPS patch total height.
3. A photo of the Amazon M3 assortment's label or compartments (does it have M3×25 button heads, sealing washers, M4×10?).
4. Confirm there's only one Qwiic Buzzer and no 18650 cells on hand.

## Verified vs inferred
- **Verified:** CAD values (source plus STL extents: cap 62 × 142 × 20.5 / 7, pod 92 × 68 × 24.5, cw 88 × 74 × 30); the repo order records; the makerdiary email; P124, P122, P123 and 1781 specs and prices (live pages today).
- **Inferred:** the "never bought P122/1781" conclusion (from the repo orders and slip; the Amazon/Voltaic/Adafruit receipts aren't in the connected Gmail, and orders-2026-09-26.md says Amazon receipts go elsewhere); the LiPo dimensions; the screw-kit contents; the resized-cap print time.
- **Not done:** no CAD edited yet, nothing bought, no emails sent.
