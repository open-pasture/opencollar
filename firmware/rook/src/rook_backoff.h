/* SPDX-License-Identifier: Apache-2.0 */
/*
 * Retry policy for the v1 HTTP binding (protocol/v2/http.md §5 and §8):
 * network/TLS error, timeout or 5xx: 30 s doubling to 30 min, +-25 % jitter;
 * 429/503 honour Retry-After (at most 1 h); 401 retries hourly.
 * Plain C, host-testable: the jitter source is injected.
 */
#ifndef ROOK_BACKOFF_H
#define ROOK_BACKOFF_H

#include <stdbool.h>
#include <stdint.h>

#define ROOK_BACKOFF_MIN_S 30
#define ROOK_BACKOFF_MAX_S 1800
#define ROOK_RETRY_AFTER_MAX_S 3600
#define ROOK_UNAUTH_RETRY_S 3600

/* What to do with what was sent, from the HTTP answer (http.md §8) */
enum rook_http_action {
	ROOK_ACT_DONE,  /* 2xx: drop what was sent */
	ROOK_ACT_DROP,  /* 400, 403, 404 on an ack: drop, log, never resend unchanged */
	ROOK_ACT_SPLIT, /* 413: split and retry */
	ROOK_ACT_RETRY, /* 429, 5xx, network: keep, back off */
	ROOK_ACT_UNAUTH, /* 401: keep, stop, retry hourly */
};

/* status <= 0 means a network/TLS error or no answer */
enum rook_http_action rook_http_action(int status, int is_ack);

/* GET /boundary: 409 is the server's safety gate refusing to send the boundary
 * (not a fault, nothing to retry sooner): it reads as 204, nothing new. */
int rook_boundary_status(int status);

/*
 * The report batch cap after a POST that sent `sent` fixes with cap `cur`:
 * 413 halves it (from what was sent, at least 1); a 2xx restores `max`;
 * anything else keeps `cur`. *drop_one: a 413 for a single fix (it can't be
 * split; drop it rather than stall the queue).
 */
uint16_t rook_batch_next(int status, uint16_t cur, uint16_t sent, uint16_t max, bool *drop_one);

struct rook_backoff {
	uint32_t next_s; /* The next plain backoff delay, before jitter */
	uint32_t (*rand32)(void *ctx);
	void *rand_ctx;
};

void rook_backoff_init(struct rook_backoff *b, uint32_t (*rand32)(void *), void *ctx);
void rook_backoff_reset(struct rook_backoff *b);
/*
 * Seconds to wait before retrying after this answer. retry_after_s < 0:
 * no Retry-After header. Returns 0 for DONE/DROP/SPLIT (go on at once).
 */
uint32_t rook_backoff_delay(struct rook_backoff *b, int status, int32_t retry_after_s);

#endif
