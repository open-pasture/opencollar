/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "test.h"

#include "app.h"
#include "fence_demo.h"
#include "gnss_fake.h"
#include "store_ram.h"

int main(void)
{
	struct starling_app app;
	struct gnss_fake fake;
	const struct gnss_track_point *pts;
	size_t n;
	struct starling_fence_blob blob;
	int ticks = 0;

	store_ram_reset();
	pts = gnss_fake_demo_track(&n);
	gnss_fake_init(&fake, pts, n, false);
	starling_app_init(&app, false);
	starling_app_bind_gnss(&app, GNSS_BACKEND_FAKE, gnss_fake_ops(), &fake);
	CHECK(starling_app_boot(&app, 0) == 0);

	memset(&blob, 0, sizeof(blob));
	blob.freshness.fence_seq = 1;
	blob.verified = true;
	blob.n_vertices = STARLING_DEMO_FENCE_N;
	memcpy(blob.vertices, STARLING_DEMO_FENCE, sizeof(STARLING_DEMO_FENCE));
	blob.warn_m = 5.0;
	blob.hysteresis_m = 1.0;
	CHECK(starling_app_set_fence(&app, &blob, 0) == 1);

	printf("starling demo (fake GNSS)\n");
	printf("t_ms\tstate\tmargin\tcue\tfence_seq\n");
	for (int64_t t = 0; t <= 14000; t += 1000) {
		struct starling_tick_out out = starling_app_tick(&app, t);

		printf("%lld\t%s\t%.1f\t%s\t%u\n", (long long)t, geofence_state_str(out.geo.state),
		       out.geo.margin_m, cue_kind_str(out.cue.kind), out.fence_seq);
		ticks++;
		CHECK(out.fenced);
		CHECK(out.fence_seq == 1);
	}
	CHECK(ticks == 15);
	return test_done("demo");
}
