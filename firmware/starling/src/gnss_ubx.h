/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * UART backend skeleton for u-blox MAX-M10S class modules (UBX + NMEA).
 * Parsing is incremental; host builds compile a UART-less stub.
 * Protocol reference: u-blox M10 interface description (public).
 */
#ifndef STARLING_GNSS_UBX_H
#define STARLING_GNSS_UBX_H

#include "gnss.h"

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define GNSS_UBX_RX_CAP 512

struct gnss_ubx_uart {
	/* Platform hooks: return bytes read / written, or negative errno. */
	int (*uart_read)(void *io, uint8_t *buf, size_t cap);
	int (*uart_write)(void *io, const uint8_t *buf, size_t len);
	void *io;

	uint8_t rx[GNSS_UBX_RX_CAP];
	size_t rx_len;
	struct gnss_fix last;
	bool have_fix;
};

void gnss_ubx_init(struct gnss_ubx_uart *u);
const struct gnss_ops *gnss_ubx_ops(void);

/* Feed raw UART bytes (tests / IRQ bottom half). Returns fixes parsed. */
int gnss_ubx_feed(struct gnss_ubx_uart *u, const uint8_t *data, size_t len);

#ifdef __cplusplus
}
#endif

#endif
