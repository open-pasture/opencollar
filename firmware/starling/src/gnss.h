/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * GNSS driver abstraction for Starling. Backends:
 *   - fake: scripted tracks (host / no-fix demo)
 *   - ubx:  UART UBX/NMEA for u-blox MAX-M10S class (I2C optional later)
 *
 * Written from the public u-blox interface description; no GPL code.
 */
#ifndef STARLING_GNSS_H
#define STARLING_GNSS_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum gnss_backend {
	GNSS_BACKEND_FAKE = 0,
	GNSS_BACKEND_UBX_UART,
};

struct gnss_fix {
	bool valid;
	double lat;
	double lon;
	double accuracy_m;
	bool has_time;
	int64_t utc; /* Unix seconds */
};

struct gnss_ops {
	int (*init)(void *ctx);
	/* Advance backend by dt_ms of simulated or real time; fill *fix. */
	int (*poll)(void *ctx, int64_t now_ms, struct gnss_fix *fix);
	int (*sleep)(void *ctx);
	int (*wake)(void *ctx);
};

struct gnss {
	enum gnss_backend backend;
	const struct gnss_ops *ops;
	void *ctx;
};

void gnss_bind(struct gnss *g, enum gnss_backend backend, const struct gnss_ops *ops, void *ctx);

static inline int gnss_init(struct gnss *g)
{
	return g->ops && g->ops->init ? g->ops->init(g->ctx) : -1;
}

static inline int gnss_poll(struct gnss *g, int64_t now_ms, struct gnss_fix *fix)
{
	return g->ops && g->ops->poll ? g->ops->poll(g->ctx, now_ms, fix) : -1;
}

#ifdef __cplusplus
}
#endif

#endif
