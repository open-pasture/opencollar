/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#include "gnss_fake.h"

#include <string.h>

void gnss_fake_init(struct gnss_fake *f, const struct gnss_track_point *pts, size_t n, bool loop)
{
	memset(f, 0, sizeof(*f));
	f->pts = pts;
	f->n = n;
	f->loop = loop;
}

static int fake_init(void *ctx)
{
	struct gnss_fake *f = ctx;

	f->i = 0;
	f->start_ms = -1;
	return 0;
}

static int fake_poll(void *ctx, int64_t now_ms, struct gnss_fix *fix)
{
	struct gnss_fake *f = ctx;
	int64_t elapsed;
	size_t i;

	memset(fix, 0, sizeof(*fix));
	if (f->n == 0 || f->pts == NULL) {
		return 0;
	}
	if (f->start_ms < 0) {
		f->start_ms = now_ms;
	}
	elapsed = now_ms - f->start_ms;

	i = f->i;
	while (i + 1 < f->n && f->pts[i + 1].t_ms <= elapsed) {
		i++;
	}
	if (f->loop && i + 1 >= f->n && elapsed > f->pts[f->n - 1].t_ms) {
		f->start_ms = now_ms;
		i = 0;
		elapsed = 0;
	}
	f->i = i;

	fix->valid = f->pts[i].valid;
	fix->lat = f->pts[i].lat;
	fix->lon = f->pts[i].lon;
	fix->accuracy_m = f->pts[i].accuracy_m;
	fix->has_time = f->pts[i].has_time;
	fix->utc = f->pts[i].utc;
	return 0;
}

static int fake_sleep(void *ctx)
{
	(void)ctx;
	return 0;
}

static int fake_wake(void *ctx)
{
	(void)ctx;
	return 0;
}

static const struct gnss_ops FAKE_OPS = {
	.init = fake_init,
	.poll = fake_poll,
	.sleep = fake_sleep,
	.wake = fake_wake,
};

const struct gnss_ops *gnss_fake_ops(void)
{
	return &FAKE_OPS;
}

/*
 * Demo track for STARLING_DEMO_FENCE (~222 m square, south edge lat=35.999):
 * inside → approach south edge (warn) → cross outside → return → fix loss.
 * ~0.00001 deg lat ≈ 1.1 m.
 */
static const struct gnss_track_point DEMO[] = {
	{0, 36.00050, -86.00050, 2.0, true, true, 1762128000},	   /* inside */
	{2000, 35.99903, -86.00050, 2.0, true, true, 1762128002},  /* approach / warn (~3 m) */
	{4000, 35.99870, -86.00050, 2.5, true, true, 1762128004},  /* cross south */
	{6000, 35.99840, -86.00050, 2.5, true, true, 1762128006},  /* outside */
	{8000, 35.99903, -86.00050, 2.0, true, true, 1762128008},  /* return warn */
	{10000, 36.00050, -86.00050, 2.0, true, true, 1762128010}, /* inside */
	{12000, 0, 0, 99.0, false, false, 0},			   /* fix loss */
	{14000, 36.00050, -86.00050, 3.0, true, true, 1762128014}, /* recover */
};

const struct gnss_track_point *gnss_fake_demo_track(size_t *n)
{
	*n = sizeof(DEMO) / sizeof(DEMO[0]);
	return DEMO;
}

void gnss_bind(struct gnss *g, enum gnss_backend backend, const struct gnss_ops *ops, void *ctx)
{
	g->backend = backend;
	g->ops = ops;
	g->ctx = ctx;
}
