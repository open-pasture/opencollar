/*
 * SPDX-License-Identifier: Apache-2.0
 * adopt-newer, reject-stale/unsigned, hwm persistence across reboot.
 */
#include "test.h"

#include "fence_demo.h"
#include "fence_store.h"
#include "store_ram.h"

static struct starling_fence_blob make_blob(uint32_t seq, bool verified)
{
	struct starling_fence_blob b;

	memset(&b, 0, sizeof(b));
	b.freshness.fence_seq = seq;
	b.freshness.source_id = 1;
	b.verified = verified;
	b.n_vertices = STARLING_DEMO_FENCE_N;
	memcpy(b.vertices, STARLING_DEMO_FENCE, sizeof(STARLING_DEMO_FENCE));
	b.warn_m = 5.0;
	b.hysteresis_m = 1.0;
	b.payload_len = 4;
	b.payload[0] = (uint8_t)seq;
	return b;
}

int main(void)
{
	struct fence_store fs;
	struct starling_fence_blob a, b, stale, unsigned_blob;

	store_ram_reset();
	fence_store_init(&fs);
	CHECK(fence_store_boot(&fs) == 0);
	CHECK(!fs.has_active);
	CHECK(fence_store_hwm(&fs) == 0);

	a = make_blob(1, true);
	CHECK(fence_store_offer(&fs, &a, 2000) == 1);
	CHECK(fs.has_active);
	CHECK(fs.active.freshness.fence_seq == 1);
	CHECK(fence_store_hwm(&fs) == 1);

	stale = make_blob(1, true);
	CHECK(fence_store_offer(&fs, &stale, 2001) == 0);

	stale = make_blob(0, true);
	CHECK(fence_store_offer(&fs, &stale, 2002) == 0);

	unsigned_blob = make_blob(2, false);
	CHECK(fence_store_offer(&fs, &unsigned_blob, 2003) == 0);
	CHECK(fence_store_hwm(&fs) == 1);

	b = make_blob(2, true);
	CHECK(fence_store_offer(&fs, &b, 2004) == 1);
	CHECK(fence_store_hwm(&fs) == 2);

	store_ram_reboot();
	{
		struct fence_store fs2;

		fence_store_init(&fs2);
		CHECK(fence_store_boot(&fs2) == 0);
		CHECK(fs2.has_active);
		CHECK(fs2.active.freshness.fence_seq == 2);
		CHECK(fence_store_hwm(&fs2) == 2);
		/* Cannot roll back after reboot */
		stale = make_blob(1, true);
		CHECK(fence_store_offer(&fs2, &stale, 3000) == 0);
		CHECK(fence_store_hwm(&fs2) == 2);
	}

	return test_done("fence_store");
}
