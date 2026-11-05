/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Starling welfare caps from PR #2 (cue.h WELFARE_DEFAULT_*):
 *   - enforce at and over max_outside_cues
 *   - auto shut-off latch after escape_cycle_limit
 *   - fence move / cue_rearm never clears shut-off
 *   - caps survive a gossip/fence-offer path unchanged
 * Audio/cue gate only; does not enable pulse.
 */
#include "test.h"

#include "app.h"
#include "fence_demo.h"
#include "gnss_fake.h"
#include "store_ram.h"
#include "welfare.h"

#include <string.h>

static struct starling_fence_blob demo_blob(uint32_t seq)
{
	struct starling_fence_blob b;

	memset(&b, 0, sizeof(b));
	b.freshness.fence_seq = seq;
	b.verified = true;
	b.n_vertices = STARLING_DEMO_FENCE_N;
	memcpy(b.vertices, STARLING_DEMO_FENCE, sizeof(STARLING_DEMO_FENCE));
	b.warn_m = 5.0;
	b.hysteresis_m = 1.0;
	return b;
}

static struct cue_command step_geo(struct cue *c, enum geofence_state st, double margin_m,
				   double warn_m, int64_t now_ms, struct welfare_hooks *wh)
{
	struct geofence_result r = {0};
	struct cue_command cmd;

	r.state = st;
	r.margin_m = margin_m;
	cmd = cue_update(c, &r, warn_m, now_ms);
	return welfare_apply(wh, cmd, &r, now_ms);
}

static void drain_welfare(struct cue *c)
{
	struct welfare_event w;

	while (cue_take_welfare(c, &w)) {
	}
}

static void test_starling_init_applies_approved_caps(void)
{
	struct starling_app app;

	store_ram_reset();
	starling_app_init(&app, false);

	CHECK(app.cue_cfg.max_outside_cues == WELFARE_DEFAULT_MAX_OUTSIDE_CUES);
	CHECK(app.cue_cfg.escape_cycle_limit == WELFARE_DEFAULT_ESCAPE_CYCLE_LIMIT);
	CHECK(app.cue_cfg.escape_cycle_window_ms == WELFARE_DEFAULT_ESCAPE_WINDOW_MS);
	CHECK(app.cue.cfg.max_outside_cues == WELFARE_DEFAULT_MAX_OUTSIDE_CUES);
	CHECK(app.cue.cfg.escape_cycle_limit == WELFARE_DEFAULT_ESCAPE_CYCLE_LIMIT);
	CHECK(app.cue.cfg.escape_cycle_window_ms == WELFARE_DEFAULT_ESCAPE_WINDOW_MS);
	/* static inline gate: compare by behaviour, not function address */
	CHECK(app.welfare.gate != NULL);
	CHECK(app.welfare.ctx == &app.cue);
	{
		struct cue_command fake = {.active = true, .kind = CUE_WARN, .freq_hz = 2700};
		struct geofence_result geo = {0};
		struct cue_command out;

		out = welfare_apply(&app.welfare, fake, &geo, 0);
		CHECK(out.active && out.kind == CUE_WARN);
		app.cue.enforcement_off = true;
		out = welfare_apply(&app.welfare, fake, &geo, 0);
		CHECK(!out.active && out.kind == CUE_NONE);
		app.cue.enforcement_off = false;
	}
}

static void test_cap_at_and_over_limit(void)
{
	struct cue_config cfg = {0};
	struct cue c;
	struct welfare_hooks wh;
	struct welfare_event w;
	struct cue_command cmd;
	int64_t t = 0;

	cfg.warn_freq_hz = 2700;
	cfg.outside_freq_hz = 3200;
	cfg.beep_ms = 200;
	cfg.max_active_ms = 20000;
	cfg.rest_ms = 30000;
	cfg.outside_max_ms = 10000;
	welfare_config_apply_approved_caps(&cfg);
	CHECK(cfg.max_outside_cues == 3);

	cue_init(&c, &cfg);
	welfare_hooks_init_shutoff(&wh, &c);

	/* Arm inside */
	CHECK(!step_geo(&c, GEOFENCE_INSIDE, 20.0, 5.0, t += 1000, &wh).active);
	CHECK(c.armed);

	cmd = step_geo(&c, GEOFENCE_OUTSIDE, -2.0, 5.0, t += 1000, &wh);
	CHECK(cmd.active && cmd.kind == CUE_OUTSIDE && c.outside_cues == 1);

	cmd = step_geo(&c, GEOFENCE_OUTSIDE, -3.0, 5.0, t += 1000, &wh);
	CHECK(cmd.active && cmd.kind == CUE_OUTSIDE && c.outside_cues == 2);

	/* At limit: third cue allowed, then cutoff */
	cmd = step_geo(&c, GEOFENCE_OUTSIDE, -4.0, 5.0, t += 1000, &wh);
	CHECK(cmd.active && cmd.kind == CUE_OUTSIDE && c.outside_cues == 3);
	CHECK(c.pulse_cutoff);
	CHECK(cue_take_welfare(&c, &w) && w.kind == WELFARE_PULSE_CUTOFF && w.outside_cues == 3);

	/* Over limit: further outside fixes silent */
	CHECK(!step_geo(&c, GEOFENCE_OUTSIDE, -5.0, 5.0, t += 1000, &wh).active);
	CHECK(!step_geo(&c, GEOFENCE_OUTSIDE, -10.0, 5.0, t += 1000, &wh).active);
}

static void test_shutoff_latch_and_fence_does_not_rearm(void)
{
	struct starling_app app;
	struct welfare_hooks *wh;
	struct welfare_event w;
	int64_t t = 0;
	uint8_t cycles_before;
	struct starling_fence_blob blob;

	store_ram_reset();
	starling_app_init(&app, false);
	wh = &app.welfare;
	CHECK(starling_app_boot(&app, 0) == 0);

	blob = demo_blob(1);
	CHECK(starling_app_set_fence(&app, &blob, 0) == 1);

	for (int cycle = 1; cycle <= 3; cycle++) {
		CHECK(!step_geo(&app.cue, GEOFENCE_INSIDE, 20.0, 5.0, t += 1000, wh).active);
		step_geo(&app.cue, GEOFENCE_OUTSIDE, -2.0, 5.0, t += 1000, wh);
		step_geo(&app.cue, GEOFENCE_OUTSIDE, -3.0, 5.0, t += 1000, wh);
		step_geo(&app.cue, GEOFENCE_OUTSIDE, -4.0, 5.0, t += 1000, wh);
		drain_welfare(&app.cue);
		CHECK(!step_geo(&app.cue, GEOFENCE_INSIDE, 20.0, 5.0, t += 1000, wh).active);
		CHECK(cue_take_welfare(&app.cue, &w) && w.kind == WELFARE_RETURNED &&
		      w.escape_cycles == (uint8_t)cycle);
	}

	CHECK(app.cue.enforcement_off);
	CHECK(cue_take_welfare(&app.cue, &w) && w.kind == WELFARE_AUTO_SHUTOFF);
	CHECK(!cue_enforcement_active(&app.cue));

	/* Fence move / cue_rearm must not clear shut-off */
	cycles_before = app.cue.escape_cycles;
	blob = demo_blob(2);
	CHECK(starling_app_set_fence(&app, &blob, (uint32_t)t) == 1);
	CHECK(app.cue.enforcement_off);
	CHECK(app.cue.escape_cycles == cycles_before);

	/* Hook still suppresses any residual active cue */
	{
		struct cue_command fake = {.active = true, .kind = CUE_WARN, .freq_hz = 2700};
		struct geofence_result geo = {0};
		struct cue_command out = welfare_apply(wh, fake, &geo, t);

		CHECK(!out.active && out.kind == CUE_NONE);
	}

	/* Serial caretaker path clears; gossip must never call this */
	starling_app_caretaker_rearm(&app, t += 1000);
	CHECK(!app.cue.enforcement_off);
	CHECK(app.cue.escape_cycles == 0);
	CHECK(cue_take_welfare(&app.cue, &w) && w.kind == WELFARE_ENFORCEMENT_RESUMED);
}

static void test_caps_survive_gossip_fence_path(void)
{
	struct starling_app app;
	struct gnss_fake fake;
	struct gnss_track_point pts[] = {
		{0, 36.00050, -86.00050, 2.0, true, true, 1762128000},
		{1000, 36.00050, -86.00050, 2.0, true, true, 1762128001},
	};
	struct starling_fence_blob blob;
	uint8_t max_cues;
	uint8_t escape_lim;
	uint32_t window_ms;

	store_ram_reset();
	gnss_fake_init(&fake, pts, 2, false);
	starling_app_init(&app, false);
	starling_app_bind_gnss(&app, GNSS_BACKEND_FAKE, gnss_fake_ops(), &fake);
	CHECK(starling_app_boot(&app, 0) == 0);

	max_cues = app.cue.cfg.max_outside_cues;
	escape_lim = app.cue.cfg.escape_cycle_limit;
	window_ms = app.cue.cfg.escape_cycle_window_ms;
	CHECK(max_cues == WELFARE_DEFAULT_MAX_OUTSIDE_CUES);
	CHECK(escape_lim == WELFARE_DEFAULT_ESCAPE_CYCLE_LIMIT);
	CHECK(window_ms == WELFARE_DEFAULT_ESCAPE_WINDOW_MS);

	blob = demo_blob(10);
	CHECK(starling_app_set_fence(&app, &blob, 100) == 1);
	(void)starling_app_tick(&app, 1000);

	/* Gossip/fence offer must not rewrite welfare caps */
	CHECK(app.cue.cfg.max_outside_cues == max_cues);
	CHECK(app.cue.cfg.escape_cycle_limit == escape_lim);
	CHECK(app.cue.cfg.escape_cycle_window_ms == window_ms);
	CHECK(app.cue_cfg.max_outside_cues == WELFARE_DEFAULT_MAX_OUTSIDE_CUES);
	CHECK(app.cue_cfg.escape_cycle_limit == WELFARE_DEFAULT_ESCAPE_CYCLE_LIMIT);
	CHECK(app.cue_cfg.escape_cycle_window_ms == WELFARE_DEFAULT_ESCAPE_WINDOW_MS);

	blob = demo_blob(11);
	CHECK(starling_app_set_fence(&app, &blob, 200) == 1);
	(void)starling_app_tick(&app, 2000);

	CHECK(app.cue.cfg.max_outside_cues == WELFARE_DEFAULT_MAX_OUTSIDE_CUES);
	CHECK(app.cue.cfg.escape_cycle_limit == WELFARE_DEFAULT_ESCAPE_CYCLE_LIMIT);
	CHECK(app.cue.cfg.escape_cycle_window_ms == WELFARE_DEFAULT_ESCAPE_WINDOW_MS);
}

int main(void)
{
	test_starling_init_applies_approved_caps();
	test_cap_at_and_over_limit();
	test_shutoff_latch_and_fence_does_not_rearm();
	test_caps_survive_gossip_fence_path();
	return test_done("welfare_caps");
}
