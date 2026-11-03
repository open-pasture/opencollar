/*
 * SPDX-License-Identifier: Apache-2.0
 * Drive the fence + cue loop from the fake GNSS demo track.
 */
#include "test.h"

#include "app.h"
#include "fence_demo.h"
#include "gnss_fake.h"
#include "store_ram.h"

static struct starling_fence_blob demo_blob(uint32_t seq)
{
	struct starling_fence_blob b;

	memset(&b, 0, sizeof(b));
	b.freshness.fence_seq = seq;
	b.verified = true;
	b.n_vertices = STARLING_DEMO_FENCE_N;
	memcpy(b.vertices, STARLING_DEMO_FENCE, sizeof(STARLING_DEMO_FENCE));
	b.warn_m = 5.0;
	b.hysteresis_m = 1.0;
	return b;
}

int main(void)
{
	struct starling_app app;
	struct gnss_fake fake;
	const struct gnss_track_point *pts;
	size_t n;
	bool saw_inside = false, saw_outside = false, saw_warn = false, saw_loss = false;
	bool saw_cue = false;

	store_ram_reset();
	pts = gnss_fake_demo_track(&n);
	gnss_fake_init(&fake, pts, n, false);

	starling_app_init(&app, false);
	starling_app_bind_gnss(&app, GNSS_BACKEND_FAKE, gnss_fake_ops(), &fake);
	CHECK(starling_app_boot(&app, 0) == 0);

	{
		struct starling_fence_blob blob = demo_blob(1);

		CHECK(starling_app_set_fence(&app, &blob, 0) == 1);
	}

	for (int64_t t = 0; t <= 15000; t += 500) {
		struct starling_tick_out out = starling_app_tick(&app, t);

		CHECK(out.fenced);
		if (out.geo.state == GEOFENCE_INSIDE) {
			saw_inside = true;
		}
		if (out.geo.state == GEOFENCE_WARNING) {
			saw_warn = true;
		}
		if (out.geo.state == GEOFENCE_OUTSIDE) {
			saw_outside = true;
		}
		if (out.geo.state == GEOFENCE_UNKNOWN) {
			saw_loss = true;
		}
		if (out.cue.active) {
			saw_cue = true;
		}
	}

	CHECK(saw_inside);
	CHECK(saw_outside);
	CHECK(saw_warn || saw_outside);
	CHECK(saw_loss);
	CHECK(saw_cue);
	return test_done("geofence_fake");
}
