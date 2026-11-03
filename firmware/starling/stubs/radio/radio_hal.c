/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#include "radio_hal.h"

#include <string.h>

int radio_hal_stub_init(void *ctx)
{
	(void)ctx;
	return 0;
}

int radio_hal_stub_sleep(void *ctx)
{
	(void)ctx;
	return 0;
}

int radio_hal_stub_rx_window(void *ctx, uint32_t window_ms)
{
	(void)ctx;
	(void)window_ms;
	return 0;
}

int radio_hal_stub_tx(void *ctx, const uint8_t *frame, size_t len)
{
	(void)ctx;
	(void)frame;
	(void)len;
	return 0;
}

int radio_hal_stub_rx_poll(void *ctx, uint8_t *buf, size_t cap)
{
	(void)ctx;
	(void)buf;
	(void)cap;
	return 0;
}

void radio_hal_ops_stub(struct radio_hal *hal)
{
	memset(hal, 0, sizeof(*hal));
	hal->init = radio_hal_stub_init;
	hal->sleep = radio_hal_stub_sleep;
	hal->rx_window = radio_hal_stub_rx_window;
	hal->tx = radio_hal_stub_tx;
	hal->rx_poll = radio_hal_stub_rx_poll;
}
