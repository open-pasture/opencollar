# Board design phase: how we work

Set up 2026-09-26. The plan and costs are in `BOARD-DESIGN.md`; this is the day-to-day method.

## Toolchain (installed on Cody's Mac)

| Tool | Version | Role |
| --- | --- | --- |
| KiCad | 10.0.6 | Board editor, libraries, checks, Gerber export. `/Applications/KiCad` |
| `kicad-cli` | 10.0.6 | Headless design-rule checks (DRC), renders, Gerbers, BOM. Linked in `~/.local/bin` |
| `kicad-python` | KiCad's bundled Python 3.9 with `pcbnew` | Scripts that build and edit boards. Wrapper in `~/.local/bin` |
| SKiDL | 2.3.0 (MIT) | The schematic, written as Python, compiled to a KiCad netlist |
| kicad-python (package) | 0.8.0 | KiCad 10's live API, for driving an open KiCad window later |
| uv | | Python environments per board project |

**Why SKiDL, not atopile:** atopile's standalone command-line tool is in maintenance mode and being replaced by a hosted app that needs an account. SKiDL is plain Python, MIT-licensed, has no account, and fits the "agents write text, humans review diffs" approach.

**Not installed yet:**
- **Freerouting** (autorouter). Needs Java; install when we reach layout.
- A **KiCad MCP server**. Worth trying once there's a real board to drive.

## Repo layout

```
hardware/
  carrier/                 carrier board (first board)
    pyproject.toml         SKiDL + kicad-python, managed by uv
    env.sh                 points SKiDL at KiCad's libraries
    smoke.py               toolchain check (LED + resistor + header)
    netlist_to_pcb.py      netlist -> .kicad_pcb with footprints and nets
    build/                 generated files (gitignored)
  integrated/              the full board (later)
```

Generated files stay out of git. The source of truth is the Python schematic plus the hand-edited `.kicad_pcb` layout once layout starts.

## The loop

```
spec (markdown) -> schematic.py (SKiDL) -> netlist -> .kicad_pcb -> DRC + render -> review
```

1. **Spec first.** Every board starts as a short markdown spec: what plugs in, every connector and its pinout, power paths, board outline and mounting holes, and which reference design each section copies. Nothing gets drawn until the spec is agreed.
2. **Schematic as code.** Each circuit block is a Python function (power, charger, buzzer, connectors) with the datasheet section it follows cited in a comment. `uv run python schematic.py` writes the netlist.
3. **Automatic checks every time.** SKiDL's electrical rules check (unconnected pins, drivers fighting); then `netlist_to_pcb.py` and `kicad-cli pcb drc`.
4. **Render and look.** `kicad-cli pcb render` produces top and bottom images. The agent reviews its own renders before showing anyone, the same way as the Blender loop in `DESIGN-TOOLING.md`.
5. **Layout in KiCad.** Scripts do the first placement from the shell outline; power and (later) radio sections are placed by hand following the reference layouts; simple nets can go to Freerouting. From here the `.kicad_pcb` is committed and edited in place.
6. **Review gates** before ordering:
   - Self-review: every pin checked against its datasheet, a power budget, DRC clean.
   - Cody reviews renders and the spec.
   - Integrated board only: Nordic DevZone schematic and layout review.
7. **Order** 5 boards from JLCPCB (Gerbers, BOM and pick-and-place from `kicad-cli`), then bring them up with the current-limited bench supply.

Commands:

```sh
cd hardware/carrier && source env.sh
uv run python smoke.py                                  # netlist in build/
kicad-python netlist_to_pcb.py build/smoke.net build/smoke.kicad_pcb
kicad-cli pcb drc --output build/drc.rpt build/smoke.kicad_pcb
kicad-cli pcb render --side top --output build/top.png build/smoke.kicad_pcb
```

The carrier board itself (rev A2):

```sh
cd hardware/carrier && source env.sh
uv run python schematic.py                                   # ERC + build/carrier.net
kicad-python layout.py build/carrier.net build/carrier.kicad_pcb   # placement, pours, silkscreen
kicad-cli pcb drc --severity-all --format json --output build/drc.json build/carrier.kicad_pcb
kicad-cli pcb render --side top --output build/top.png build/carrier.kicad_pcb
kicad-cli pcb render --side bottom --output build/bottom.png build/carrier.kicad_pcb
```

Routing (rev A2): Inky routed the board in HeyPCB. Its export is committed as `pcb/heypcb/`, and `finish_routing.py` redoes the charger block from it and writes the routed board:

```sh
kicad-python finish_routing.py pcb/heypcb/opencollar-carrier.kicad_pcb pcb/carrier.kicad_pcb
kicad-cli pcb drc --severity-all --refill-zones --format json --output build/drc.json pcb/carrier.kicad_pcb
```

## Known gap: a readable schematic

SKiDL writes netlists, not KiCad schematic sheets. That's fine for the carrier board, where agents and diffs do the reviewing. Nordic's review (and most humans) want a schematic PDF. Before the integrated board, either:

- generate schematic sheets from the same Python (write `.kicad_sch` directly), or
- draw the integrated board's schematic natively in KiCad, with agents editing the `.kicad_sch` text.

Decide when the carrier board is done.

## Rules we hold to

- **Datasheets over breakout boards.** SparkFun and Adafruit designs are share-alike licensed; use them to check our work, not as a source (see `BOARD-DESIGN.md`).
- **JLCPCB-stocked parts** unless there's a reason not to, preferring "basic" parts (no setup fee).
- **Test pads** for every rail and programming line, so a fixture can test the board later (`MANUFACTURING.md`).
- **Every board revision gets a build-log entry:** what changed, why, and what bring-up found.

## First task: the carrier board spec

`hardware/carrier/SPEC.md`, covering:
- Female headers for the nRF9151 Connect Kit, the MAX-M10S breakout and the IMU (or Qwiic sockets)
- bq24074 charger circuit (from TI's datasheet), thermistor connector
- Buzzer driver and piezo footprint
- JST-PH connectors for the battery and panels; the strap harness connector
- Board outline and mounting holes, from the printed top unit's inside dimensions
- Test pads
