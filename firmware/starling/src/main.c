/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Starling Zephyr entry (nRF52840). Uses fake GNSS until the u-blox arrives.
 */
#include <string.h>

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include "app.h"
#include "store.h"
#include "fence_demo.h"
#include "gnss_fake.h"
#include "gnss_ubx.h"

LOG_MODULE_REGISTER(starling, LOG_LEVEL_INF);

#ifndef CONFIG_STARLING_SERVE
#define CONFIG_STARLING_SERVE 0
#endif

#ifndef CONFIG_STARLING_GNSS_FAKE
#define CONFIG_STARLING_GNSS_FAKE 1
#endif

static struct starling_app app;
static struct gnss_fake fake;
static struct gnss_ubx_uart ubx;

int main(void)
{
	struct starling_fence_blob blob;
	int64_t now_ms = 0;

	LOG_INF("OpenCollar Starling %s", STARLING_FW_VERSION);

	starling_app_init(&app, IS_ENABLED(CONFIG_STARLING_SERVE));

	if (IS_ENABLED(CONFIG_STARLING_GNSS_FAKE)) {
		size_t n;
		const struct gnss_track_point *pts = gnss_fake_demo_track(&n);

		gnss_fake_init(&fake, pts, n, true);
		starling_app_bind_gnss(&app, GNSS_BACKEND_FAKE, gnss_fake_ops(), &fake);
	} else {
		gnss_ubx_init(&ubx);
		starling_app_bind_gnss(&app, GNSS_BACKEND_UBX_UART, gnss_ubx_ops(), &ubx);
	}

	if (store_init() != 0) {
		LOG_WRN("store_init failed; continuing without NVS");
	}
	if (starling_app_boot(&app, 0) != 0) {
		LOG_ERR("boot failed");
		return -1;
	}

	/* Bench fence when flash is empty (pilot / fake GNSS). */
	if (!app.fenced) {
		memset(&blob, 0, sizeof(blob));
		blob.freshness.fence_seq = 1;
		blob.freshness.verified = true;
		blob.n_vertices = STARLING_DEMO_FENCE_N;
		memcpy(blob.vertices, STARLING_DEMO_FENCE, sizeof(STARLING_DEMO_FENCE));
		blob.warn_m = 5.0;
		blob.hysteresis_m = 1.0;
		starling_app_set_fence(&app, &blob, 0);
	}

	while (1) {
		struct starling_tick_out out = starling_app_tick(&app, now_ms);

		if (out.fenced) {
			LOG_INF("fence=%u %s margin=%.1f cue=%s pwr=%d", out.fence_seq,
				geofence_state_str(out.geo.state), out.geo.margin_m,
				cue_kind_str(out.cue.kind), (int)out.power);
		}
		k_msleep(500);
		now_ms += 500;
	}
	return 0;
}
