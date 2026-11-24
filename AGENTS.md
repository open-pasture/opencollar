# Agents

Project skills live in `.claude/skills/`. Read `.claude/skills/cody-mode/SKILL.md` before any work; it lists this repo's gates.

## Rules and what enforces them

| Rule | Enforced by |
| --- | --- |
| `firmware/tests/host/vectors/*.json` are byte copies of `protocol/vectors/`; change the source, then copy | `scripts/check-vectors.sh` (CI: Protocol vectors) |
| A change to `protocol/vectors/` adds a `protocol/CHANGELOG.md` line naming openpasture's `OPENCOLLAR_REF` pin, and that pin moves in an openpasture PR | `scripts/check-vectors.sh origin/main` (CI, on pull requests) |
| Collar logic, host tests and protocol tools take time as an input and never read the wall clock, so fixed test dates never age out | `scripts/check-no-wall-clock.sh` (CI: Firmware host tests) |
