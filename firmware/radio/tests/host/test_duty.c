/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_duty.h"

#include <stdio.h>

static int fails;

static void check(int cond, const char *msg)
{
	if (!cond) {
		fprintf(stderr, "FAIL %s\n", msg);
		fails++;
	}
}

int main(void)
{
	struct radio_duty d;

	radio_duty_init(&d, 20000, 0, 20000, 400000); /* 400 ms dwell / 20 s */

	check(radio_duty_allow(&d, 0, 903900000, 100000), "first ok");
	radio_duty_account(&d, 0, 903900000, 100000);
	check(radio_duty_allow(&d, 1000, 903900000, 300000), "still under dwell");
	radio_duty_account(&d, 1000, 903900000, 300000);
	check(!radio_duty_allow(&d, 2000, 903900000, 1), "dwell exhausted");

	/* New channel resets dwell. */
	check(radio_duty_allow(&d, 2000, 905500000, 100000), "new channel ok");

	/* After dwell window rolls, same channel ok again. */
	check(radio_duty_allow(&d, 25000, 903900000, 100000), "window rolled");

	if (fails) {
		return 1;
	}
	puts("ok");
	return 0;
}
