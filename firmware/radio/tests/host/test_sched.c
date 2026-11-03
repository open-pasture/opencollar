/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_sched.h"
#include "radio_backoff.h"

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
	struct radio_sched s;
	struct radio_sched_cfg cfg = {
		.rx_period_ms = 1000,
		.rx_window_ms = 100,
		.beacon_period_ms = 5000,
		.beacon_jitter_ms = 0,
		.cad_before_beacon = true,
		.cad_wake_period_ms = 0,
	};
	uint32_t wake = 0;
	enum radio_sched_action a;

	radio_backoff_seed(42);
	radio_sched_init(&s, &cfg, 0);

	a = radio_sched_poll(&s, 0, &wake);
	check(a == RADIO_SCHED_RX_WINDOW, "start in RX");
	a = radio_sched_poll(&s, 50, &wake);
	check(a == RADIO_SCHED_RX_WINDOW, "still RX");
	a = radio_sched_poll(&s, 100, &wake);
	check(a == RADIO_SCHED_SLEEP || a == RADIO_SCHED_RX_WINDOW, "end RX");

	/* Force beacon time. */
	s.next_beacon_ms = 200;
	a = radio_sched_poll(&s, 200, &wake);
	check(a == RADIO_SCHED_BEACON, "beacon due");
	radio_sched_beacon_done(&s, 200);
	check(s.next_beacon_ms == 5200, "next beacon armed");

	if (fails) {
		return 1;
	}
	puts("ok");
	return 0;
}
