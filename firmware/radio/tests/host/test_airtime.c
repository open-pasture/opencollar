/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_airtime.h"

#include <stdio.h>

static int fails;

static void expect_eq(const char *name, uint32_t got, uint32_t want)
{
	if (got != want) {
		fprintf(stderr, "FAIL %s: got %u want %u\n", name, got, want);
		fails++;
	}
}

int main(void)
{
	struct radio_airtime_params p = {
		.bandwidth_hz = 125000,
		.spreading_factor = 8,
		.coding_rate = 5,
		.preamble_symbols = 8,
		.explicit_header = true,
		.crc_on = true,
	};

	expect_eq("tsym_sf8_125k", radio_airtime_tsym_us(8, 125000), 2048);

	/* Golden values from AN1200.13 (this implementation). See docs/AIRTIME.md. */
	expect_eq("sf8_0", radio_airtime_packet_us(&p, 0), 51712);
	expect_eq("sf8_16", radio_airtime_packet_us(&p, 16), 92672);
	expect_eq("sf8_64", radio_airtime_packet_us(&p, 64), 215552);
	expect_eq("sf8_128", radio_airtime_packet_us(&p, 128), 379392);
	expect_eq("sf8_222", radio_airtime_packet_us(&p, 222), 614912);

	p.spreading_factor = 7;
	expect_eq("sf7_16", radio_airtime_packet_us(&p, 16), 51456);
	p.spreading_factor = 10;
	expect_eq("sf10_16", radio_airtime_packet_us(&p, 16), 329728);

	if (fails) {
		return 1;
	}
	puts("ok");
	return 0;
}
