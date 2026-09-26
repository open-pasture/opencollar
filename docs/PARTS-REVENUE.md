# Making money from the open parts list

Two options: affiliate links on the published parts list, and kits we sell. Researched 2026-09-26.

## Affiliate programs for the vendors on our list

| Vendor | Program | Rate | Notes |
| --- | --- | --- | --- |
| SparkFun | [Yes](https://www.sparkfun.com/affiliate-program) | **10 %**, SparkFun Original products only | Our IMU, Qwiic cables and MAX-M10S board are SparkFun Originals (the M10S is backordered there right now; we're buying it at DigiKey) |
| Amazon | Associates | ~2.5–3 % | Electronics 2.5 %, industrial supplies 3 %. Rates change quarterly |
| GoPro | [Yes](https://gopro.com/en/us/legal/gopro-affiliate-program) | 3 % | 30-day cookie |
| Adafruit | [No](https://blog.adafruit.com/2009/09/14/adafruit-has-never-and-will-never-do-any-affiliate-programs-period/) | — | Publicly refuses affiliate programs |
| DigiKey | Unclear | Low if it exists | No rate published; needs a direct inquiry |
| TI, Voltaic, Pololu, United Lithium, K&J, Heritage | Not found | — | Worth asking Voltaic and Pololu directly |

### What that earns

A collar build is roughly $450–550 in parts (excluding test gear like the PPK2).

| Source | Qualifying spend | Commission |
| --- | --- | --- |
| SparkFun Originals (IMU, cables, MAX-M10S if bought at SparkFun) | ~$90 | ~$9 |
| Amazon | ~$60 | ~$2 |
| GoPro (camera builds only) | ~$220 | ~$7 |
| **Per build** | | **~$10–20** |

So affiliate income is about **$10–20 per collar built**: fine as a bonus, not a business until thousands of people build collars. Routing more parts through SparkFun (which sells many third-party parts, but pays only on its own) helps a little.

**Rules:** US law (FTC) requires a clear affiliate disclosure next to the links. The open hardware community is sensitive to hidden affiliate links, so disclose plainly at the top of the parts list and keep a plain, non-affiliate link for every part.

## Kits

Buy parts in volume, sell complete kits. This is where the money is, and it's a better experience for builders: one box instead of twelve orders.

### Tiers

| Kit | What's in it | Who it's for |
| --- | --- | --- |
| **Electronics kit** | Every board and module, pre-flashed firmware, harness pre-made, cells shipped separately | Builders who print their own shell |
| **Complete kit** | Electronics kit + printed shell set + strap + hardware | Farmers and tinkerers who want to assemble but not source or print |
| **Assembled collar** | Built, tested, ready to strap on | Farmers who just want a collar (this becomes the sold OpenCollar) |

### Rough margins (breakout-board version, 100-kit batch)

- Retail cost to source it yourself: ~$450–550 (collar, no camera).
- Our cost buying 100 kits' worth: typically 20–35 % less through distributor price breaks and direct buys, plus our labour to flash, test and pack.
- **Sell at or slightly below the cost of sourcing it yourself** and the margin is roughly **$100–200 per kit**, about 10× the affiliate income.
- Once V1-beta has its own custom board, the kit gets much cheaper to make (the breakout boards and eval kits are most of the cost), and the margin grows.

### Things to sort out before selling kits

- **Batteries:** lithium cells need UN38.3-certified cells, hazmat labelling and restricted shipping methods. Simplest start: kits exclude cells, with a link to buy them, or ship cells via a supplier who handles it.
- **Radio certification:** kits built from pre-certified modules (nRF9151, u-blox) are generally fine to sell as kits; an assembled product with our own board needs FCC certification.
- **Support and returns:** a kit business is also a support business. Good build docs reduce this a lot.
- **Liability:** once the pulse module exists, stimulus kits need extra care (instructions, warnings, welfare guidance).

## Recommendation

Do both, in order:
1. **Now:** publish the parts list with affiliate links where they exist (SparkFun first), plainly disclosed, plus plain links.
2. **After the prototype works:** sell electronics and complete kits from a first batch of ~25–100.
3. **After V1-beta:** assembled collars on the custom board become the main product; kits stay for builders.
