/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * adopt-newer, reject-stale/unsigned, version persistence across reboot.
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
	b.freshness.issued_at = 1000 + (int64_t)seq;
	b.freshness.verified = verified;
	b.n_vertices = STARLING_DEMO_FENCE_N;
	memcpy(b.vertices, STARLING_DEMO_FENCE, sizeof(STARLING_DEMO_FENCE));
	b.warn_m = 5.0;
	b.hysteresis_m = 1.0;
	snprintf((char *)b.payload, sizeof(b.payload), "fence-seq-%u", seq);
	b.payload_len = (uint16_t)strlen((char *)b.payload);
	return b;
}

int main(void)
{
	struct fence_store fs;
	struct starling_fence_blob a, b, stale, unsigned_blob;

	store_ram_reset();
	fence_store_init(&fs, NULL);
	CHECK(fence_store_boot(&fs) == 0);
	CHECK(!fs.has_active);

	a = make_blob(1, true);
	CHECK(fence_store_offer(&fs, &a, 2000, true) == 1);
	CHECK(fs.has_active);
	CHECK(fs.active.freshness.fence_seq == 1);
	CHECK(fs.has_log);

	/* Equal seq rejected */
	stale = make_blob(1, true);
	CHECK(fence_store_offer(&fs, &stale, 2001, true) == 0);
	CHECK(fs.active.freshness.fence_seq == 1);

	/* Older rejected */
	stale = make_blob(0, true);
	CHECK(fence_store_offer(&fs, &stale, 2002, true) == 0);

	/* Unsigned / unverified rejected when not marked verified */
	unsigned_blob = make_blob(2, false);
	unsigned_blob.has_sig = false;
	CHECK(fence_store_offer(&fs, &unsigned_blob, 2003, false) == 0);
	CHECK(fs.active.freshness.fence_seq == 1);

	/* Newer adopted */
	b = make_blob(2, true);
	CHECK(fence_store_offer(&fs, &b, 2004, true) == 1);
	CHECK(fs.active.freshness.fence_seq == 2);
	CHECK(fs.log.fence_seq == 2);

	/* Persistence across reboot */
	store_ram_reboot();
	{
		struct fence_store fs2;

		fence_store_init(&fs2, NULL);
		CHECK(fence_store_boot(&fs2) == 0);
		CHECK(fs2.has_active);
		CHECK(fs2.active.freshness.fence_seq == 2);
		CHECK(fs2.has_log);
		CHECK(fs2.log.fence_seq == 2);
		CHECK(fs2.active.n_vertices == STARLING_DEMO_FENCE_N);
	}

	return test_done("fence_store");
}
