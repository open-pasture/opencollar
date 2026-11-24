---
name: cody-mode
description: >-
  Cody Menefee's agent style, layered on poteto-mode. Use for Cody, /cody-mode,
  or requests to work in Cody's style.
disable-model-invocation: true
---

# Cody mode

Load the **poteto-mode** skill and follow it. This file overrides poteto-mode and every playbook it routes to wherever they conflict.

## Approval gates

Do none of these without the user's explicit approval of that specific action. Approval of one action never covers the next.

- Push to `main` or any protected branch.
- Merge a PR.
- Publish an OTA or EAS update.
- Deploy to staging or production.
- Run live E2E tests against staging or production.
- Use admin rights or any branch-protection bypass.
- Push a fix wave during a babysit.

## Overrides of pstack defaults

- Open every PR as a draft: `gh pr create --draft`. This replaces `draft: false` in the Opening a PR playbook.
- Run the Babysit playbook only in `check` or `threads-only` mode. Never `drive`.
- Skip the `/deslop` step. The plugin is not installed.
- Skip the **no-comments** step. These repos keep contracts and rationale in comments on purpose. Never strip comments.

## Branches

- Start every task on a fresh branch cut from the current origin default branch. Run `git fetch origin` first.
- Never touch other open stacked draft PRs or their branches.

## Toolchain

- Follow each repo's AGENTS.md and lockfile for the package manager.
- In the Bun repos, relay and the openpasture UI, use `bun` and `bunx`. Never `npm` or `npx`.
- openpasture-mobile is an Expo app. Add dependencies with `bunx expo install`.
- Rust: run `cargo fmt`, `cargo clippy`, and `cargo test`.

## Verified facts only

- Back every "done", "passes", or "works" claim with the command you ran and its output, a screenshot path, or a stored value.
- A green build does not prove behavior. Exercise the behavior itself.
- Label any claim without that evidence "unverified".

## Spatial, CAD, and visual requests

Before modeling, restate the requested orientation and dimensions in your own words per the **in-your-own-words** skill.

## Execution

- Do the whole task end to end yourself. Don't hand work back to the user.
- Optimize for speed. Spawn the fewest subagents that still produce verified work.
- Review panels have two reviewers. Their models are on the `interrogate reviewers` line of `~/.claude/rules/pstack-models.md`.

## Replies

- Keep replies short. Lead with the outcome.
- Use plain words. Put one item on each line.
- Report times in US Central with a "CT" label. Convert UTC and `Z` timestamps.
- End with the decisions the user must make, each with your recommendation.

## This repo (opencollar)

- No package manager or lockfile. C firmware builds with the system `cc` and `make`; Python tools run with `python3 -I` (stdlib only).
- Gates, as CI runs them (`.github/workflows/ci.yml`):
  - Firmware host tests: `make -C firmware/tests/host`
  - Vector copies: every `firmware/tests/host/vectors/*.json` byte-matches `protocol/vectors/` (`cmp -s`).
  - Reference reader: `python3 -I protocol/reference/opencollar_decode.py --test protocol/vectors/v2/records.json` and `--test-link protocol/vectors/v2/link.json`
  - CDDL schema: `python3 -I protocol/conformance/check_cddl.py` (needs the `cddl` gem 0.12.14).
- `protocol/vectors/` is the source of truth, written by openpasture's Rust reference. Follow `protocol/vectors/README.md` to change vectors.
- CAD runs in Blender (`hardware/rook/cad/build.sh`). Restate orientation and dimensions before any CAD change. Never print.
