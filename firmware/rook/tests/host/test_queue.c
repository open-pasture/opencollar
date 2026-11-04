/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_queue.h"
#include "test.h"

static struct rook_queue q;

int main(void)
{
	struct rook_sample s = {0};

	rook_queue_init(&q);
	CHECK(rook_queue_peek(&q, 0) == NULL);
	for (int i = 0; i < ROOK_QUEUE_CAP + 5; i++) {
		s.at = i;
		rook_queue_push(&q, &s);
	}
	CHECK(q.n == ROOK_QUEUE_CAP);
	CHECK(q.overwritten == 5);
	CHECK(rook_queue_peek(&q, 0)->at == 5);
	CHECK(rook_queue_peek(&q, ROOK_QUEUE_CAP - 1)->at == ROOK_QUEUE_CAP + 4);
	rook_queue_drop(&q, 3);
	CHECK(q.n == ROOK_QUEUE_CAP - 3 && rook_queue_peek(&q, 0)->at == 8);
	rook_queue_drop(&q, 1000);
	CHECK(q.n == 0 && rook_queue_peek(&q, 0) == NULL);
	return test_done("rook queue");
}
