# D5 plate layouts

Machine-readable: `plates.json`. **OrcaSlicer CLI is not available** in this environment — STL nests + settings are committed; **op-maker** builds 3MFs.

## P2S 256 × 256 (per Rook collar)

### Verify (PLA)

1. fit_coupon, label_coupon, clamp×2, plugs, latch, usbc_cap — ~1.5 h  
2. cap_base + cap_lid — ~6.5 h  
3. both pods base+lid — ~8.0 h  
4. cw + saddle + keeper + buckle — ~5.5 h  
5. fairings + clamps + charcoal plugs — ~4.0 h  

**Total ~25.5 h / 5 plates.**

### Field (ASA/PETG)

Same five plates; expect ~31.5 h with enclosure / slower ASA. TPU caps on a separate soft plate.

## 220 × 220 (Ender-class)

Nine plates (~28.5 h PLA / ~36 h field). Cap 76×160 fits one plate; split pod pair. ASA on stock Ender needs an enclosure — **PETG** is the reproducible baseline off Bambu.

## Starling

CAD not designed yet. Budget **~3 P2S / ~4×220** once XIAO+Wio shell exists (small cells only; share strap hardware).

## Spares

See `../SPARES.md` — target **&lt; 2 h**.
