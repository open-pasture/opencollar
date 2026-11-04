/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Small square fence used by fake-GNSS host demos (around 36N, 86W).
 */
#ifndef STARLING_FENCE_DEMO_H
#define STARLING_FENCE_DEMO_H

#include "geofence.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ~222 m square (0.002 deg lat/lon ≈ 222 m). */
static const struct geo_point STARLING_DEMO_FENCE[] = {
	{36.00100, -86.00100},
	{36.00100, -85.99900},
	{35.99900, -85.99900},
	{35.99900, -86.00100},
};

#define STARLING_DEMO_FENCE_N 4

#ifdef __cplusplus
}
#endif

#endif
