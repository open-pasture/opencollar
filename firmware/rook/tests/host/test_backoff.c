/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_backoff.h"
#include "test.h"

static uint32_t r;
static uint32_t fixed(void *ctx)
{
	(void)ctx;
	return r;
}

int main(void)
{
	struct rook_backoff b;

	CHECK(rook_http_action(200, 0) == ROOK_ACT_DONE);
	CHECK(rook_http_action(204, 0) == ROOK_ACT_DONE);
	CHECK(rook_http_action(400, 0) == ROOK_ACT_DROP);
	CHECK(rook_http_action(403, 0) == ROOK_ACT_DROP);
	CHECK(rook_http_action(404, 1) == ROOK_ACT_DROP);
	CHECK(rook_http_action(404, 0) == ROOK_ACT_RETRY);
	CHECK(rook_http_action(401, 0) == ROOK_ACT_UNAUTH);
	CHECK(rook_http_action(413, 0) == ROOK_ACT_SPLIT);
	CHECK(rook_http_action(-1, 0) == ROOK_ACT_RETRY);
	CHECK(rook_http_action(502, 0) == ROOK_ACT_RETRY);

	rook_backoff_init(&b, fixed, NULL);
	r = 0; /* lowest jitter: 0.75x */
	CHECK(rook_backoff_delay(&b, -1, -1) == 23); /* 30 - 7 */
	CHECK(rook_backoff_delay(&b, 500, -1) == 45);
	r = 0xffffffffu; /* highest: 1.25x */
	CHECK(rook_backoff_delay(&b, 500, -1) == 150); /* 120 * 1.25 */
	for (int i = 0; i < 20; i++) {
		(void)rook_backoff_delay(&b, -1, -1);
	}
	CHECK(b.next_s == ROOK_BACKOFF_MAX_S);
	r = 0x80000000u;
	{
		uint32_t d = rook_backoff_delay(&b, -1, -1);
		CHECK(d >= 1350 && d <= 2250);
	}
	CHECK(rook_backoff_delay(&b, 503, 7) == 7);
	CHECK(rook_backoff_delay(&b, 429, 99999) == ROOK_RETRY_AFTER_MAX_S);
	CHECK(rook_backoff_delay(&b, 401, -1) == ROOK_UNAUTH_RETRY_S);
	CHECK(rook_backoff_delay(&b, 200, -1) == 0 && b.next_s == ROOK_BACKOFF_MIN_S);
	return test_done("rook backoff");
}
