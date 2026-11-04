/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_backoff.h"

enum rook_http_action rook_http_action(int status, int is_ack)
{
	if (status >= 200 && status < 300) {
		return ROOK_ACT_DONE;
	}
	if (status == 400 || status == 403 || (status == 404 && is_ack)) {
		return ROOK_ACT_DROP;
	}
	if (status == 401) {
		return ROOK_ACT_UNAUTH;
	}
	if (status == 413) {
		return ROOK_ACT_SPLIT;
	}
	return ROOK_ACT_RETRY; /* 429, 5xx, network, and anything unexpected */
}

void rook_backoff_init(struct rook_backoff *b, uint32_t (*rand32)(void *), void *ctx)
{
	b->rand32 = rand32;
	b->rand_ctx = ctx;
	rook_backoff_reset(b);
}

void rook_backoff_reset(struct rook_backoff *b)
{
	b->next_s = ROOK_BACKOFF_MIN_S;
}

static uint32_t jitter(struct rook_backoff *b, uint32_t s)
{
	/* s * [0.75, 1.25] */
	uint32_t span = s / 2;
	uint32_t r = b->rand32 ? b->rand32(b->rand_ctx) : 0x80000000u;

	if (span == 0) {
		return s;
	}
	return s - s / 4 + (uint32_t)(((uint64_t)r * (span + 1)) >> 32);
}

uint32_t rook_backoff_delay(struct rook_backoff *b, int status, int32_t retry_after_s)
{
	uint32_t d;

	switch (rook_http_action(status, 0)) {
	case ROOK_ACT_DONE:
		rook_backoff_reset(b);
		return 0;
	case ROOK_ACT_DROP:
	case ROOK_ACT_SPLIT:
		return 0;
	case ROOK_ACT_UNAUTH:
		return ROOK_UNAUTH_RETRY_S;
	case ROOK_ACT_RETRY:
	default:
		break;
	}
	if ((status == 429 || status == 503) && retry_after_s >= 0) {
		return retry_after_s > ROOK_RETRY_AFTER_MAX_S ? ROOK_RETRY_AFTER_MAX_S
							      : (uint32_t)retry_after_s;
	}
	d = jitter(b, b->next_s);
	b->next_s = b->next_s >= ROOK_BACKOFF_MAX_S / 2 ? ROOK_BACKOFF_MAX_S : b->next_s * 2;
	return d;
}

int rook_boundary_status(int status)
{
	return status == 409 ? 204 : status;
}
