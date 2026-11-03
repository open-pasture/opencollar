/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_backoff.h"

#include <stdio.h>

static int fails;

int main(void)
{
	uint32_t i, v;

	radio_backoff_seed(1);
	for (i = 0; i < 50; i++) {
		v = radio_backoff_ms(i % 5, 10, 200);
		if (v < 10 || v > 200) {
			fprintf(stderr, "out of range %u\n", v);
			fails++;
		}
	}
	if (radio_backoff_ms(0, 50, 50) != 50) {
		fails++;
	}
	if (fails) {
		return 1;
	}
	puts("ok");
	return 0;
}
