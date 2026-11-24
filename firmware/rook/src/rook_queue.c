/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_queue.h"

#include <string.h>

void rook_queue_init(struct rook_queue *q)
{
	memset(q, 0, sizeof(*q));
}

void rook_queue_push(struct rook_queue *q, const struct rook_sample *s)
{
	if (q->n == ROOK_QUEUE_CAP) {
		q->head = (uint16_t)((q->head + 1) % ROOK_QUEUE_CAP);
		q->n--;
		q->overwritten++;
	}
	q->s[(q->head + q->n) % ROOK_QUEUE_CAP] = *s;
	q->n++;
}

const struct rook_sample *rook_queue_peek(const struct rook_queue *q, uint16_t i)
{
	if (i >= q->n) {
		return NULL;
	}
	return &q->s[(q->head + i) % ROOK_QUEUE_CAP];
}

void rook_queue_drop(struct rook_queue *q, uint16_t n)
{
	if (n > q->n) {
		n = q->n;
	}
	q->head = (uint16_t)((q->head + n) % ROOK_QUEUE_CAP);
	q->n -= n;
}
