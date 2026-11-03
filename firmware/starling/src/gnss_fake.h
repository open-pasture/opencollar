/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Fake GNSS: replays a scripted track so the fence runs with no hardware.
 */
#ifndef STARLING_GNSS_FAKE_H
#define STARLING_GNSS_FAKE_H

#include "gnss.h"

#ifdef __cplusplus
extern "C" {
#endif

enum gnss_track_phase {
	GNSS_TRACK_INSIDE = 0,
	GNSS_TRACK_APPROACH,
	GNSS_TRACK_CROSS,
	GNSS_TRACK_RETURN,
	GNSS_TRACK_FIX_LOSS,
};

struct gnss_track_point {
	int64_t t_ms; /* Time along the track */
	double lat;
	double lon;
	double accuracy_m;
	bool valid; /* false = fix loss */
	bool has_time;
	int64_t utc;
};

struct gnss_fake {
	const struct gnss_track_point *pts;
	size_t n;
	size_t i;
	int64_t start_ms;
	bool loop;
};

void gnss_fake_init(struct gnss_fake *f, const struct gnss_track_point *pts, size_t n, bool loop);
const struct gnss_ops *gnss_fake_ops(void);

/* Built-in demo track around a small square fence (see fence_demo.h). */
const struct gnss_track_point *gnss_fake_demo_track(size_t *n);

#ifdef __cplusplus
}
#endif

#endif
