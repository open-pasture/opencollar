/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * STUB — owned by op-fw-radio (firmware/radio, SX1262). Starling and the
 * LoRa gossip library talk to the radio only through this HAL.
 */
#ifndef OPENCOLLAR_STUB_RADIO_HAL_H
#define OPENCOLLAR_STUB_RADIO_HAL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

struct radio_hal {
	void *ctx;
	int (*init)(void *ctx);
	int (*sleep)(void *ctx);
	int (*rx_window)(void *ctx, uint32_t window_ms);
	int (*tx)(void *ctx, const uint8_t *frame, size_t len);
	/* Non-blocking: copy one received frame; return length or 0 / negative. */
	int (*rx_poll)(void *ctx, uint8_t *buf, size_t cap);
};

int radio_hal_stub_init(void *ctx);
int radio_hal_stub_sleep(void *ctx);
int radio_hal_stub_rx_window(void *ctx, uint32_t window_ms);
int radio_hal_stub_tx(void *ctx, const uint8_t *frame, size_t len);
int radio_hal_stub_rx_poll(void *ctx, uint8_t *buf, size_t cap);

void radio_hal_ops_stub(struct radio_hal *hal);

#ifdef __cplusplus
}
#endif

#endif
