/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_fence.h"

static rook_fence_sink_fn sink;
static void *sink_ctx;
static uint32_t last_seq;

void rook_fence_set_sink(rook_fence_sink_fn fn, void *ctx)
{
	sink = fn;
	sink_ctx = ctx;
}

uint32_t rook_fence_seq(void)
{
	return last_seq;
}

void rook_fence_reset(void)
{
	sink = NULL;
	sink_ctx = NULL;
	last_seq = 0;
}

struct rook_fence_result rook_fence_download(struct app *a, const char *wire, size_t len,
					     int64_t now_ms)
{
	struct rook_fence_result r = {0};

	r.code = app_boundary(a, wire, len, now_ms, &r.ack, &r.has_ack);
	if (r.code != REJECT_NONE || !r.has_ack || r.ack.status == ACK_REJECTED) {
		return r;
	}
	if (r.ack.version > last_seq) {
		last_seq = r.ack.version;
		if (sink) {
			sink(sink_ctx, r.ack.version, wire, len);
			r.handed_on = true;
		}
	}
	return r;
}
