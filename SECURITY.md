# Security

OpenCollar runs on collars worn by live animals. A collar that accepts a forged boundary, gives
up its keys, or runs firmware nobody signed can move or stress a herd, put animals on a road, or
leave them without a fence. Please report anything that could lead there privately, and give us
time to fix it before you publish.

## Report a vulnerability

Use GitHub's private reporting:
[Report a vulnerability](https://github.com/open-pasture/opencollar/security/advisories/new)
(the **Security** tab, then **Report a vulnerability**). Only the maintainers see the report.

Don't open a public issue, pull request or discussion for a vulnerability.

Include what you can: the firmware version and board, the hardware revision, the steps to
reproduce, and what an attacker gains. Test on your own collar, on the bench, never on an animal.

We acknowledge a report within 3 working days, and send a first assessment within 10. We fix
problems that can affect an animal or a collar's fence first. We credit you in the advisory
unless you ask us not to.

## Supported versions

Only the latest firmware and the current protocol version get security fixes.

## Scope

- Firmware: boundary and config verification (signatures, versions, herd, out-of-step
  commands), the cue logic and its safety limits, persistent storage of boundaries and keys.
- Provisioning: how keys get onto a collar (USB console today), locking it afterwards, and
  reading keys back out of a collar in hand.
- Firmware updates: anything that would let unsigned or downgraded firmware run.
- The device protocol in `protocol/`: message formats, signing, test vectors, anything in the
  spec that lets a server or a third party be impersonated or replayed.
- Radio links (cellular, LoRa and lead-collar relays) as they are built: anything that lets a
  nearby device inject, replay or suppress commands.
- Hardware design faults with a safety effect, for example a cue that can't be stopped.

The openpasture server, desktop app and the `op-protocol`/`op-geo` crates live in
[open-pasture/openpasture](https://github.com/open-pasture/openpasture); report those there.
If you're unsure where a problem belongs, report it here and we'll move it.

Out of scope: attacks that need the collar opened and its debug port wired up, until the
firmware claims to lock it (say so if you find that claim false), and jamming radio by
brute force.
