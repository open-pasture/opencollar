/* Cue policy: the V0 tests (unchanged), kinds, holes, episodes, track mode */
#include "v0_fixtures.h"

/* ---- V0 tests, as they were in test_main.c ---- */

static void test_cue_volume_ramps(void)
{
	struct cue c;
	struct geofence_result r = {.state = GEOFENCE_WARNING};
	struct cue_command cmd;

	cue_init(&c, &CUE_CFG);

	r.margin_m = 4.9;
	cmd = cue_update(&c, &r, 5.0, 0);
	CHECK(cmd.active && cmd.volume == 1 && cmd.freq_hz == 2730);

	r.margin_m = 0.1;
	cmd = cue_update(&c, &r, 5.0, 1000);
	CHECK(cmd.active && cmd.volume == 3);

	r.margin_m = 0.0;
	cmd = cue_update(&c, &r, 5.0, 2000);
	CHECK(cmd.volume == 4);

	r.state = GEOFENCE_INSIDE;
	cmd = cue_update(&c, &r, 5.0, 3000);
	CHECK(!cmd.active);
}

static void test_cue_rest_after_max_active(void)
{
	struct cue c;
	struct geofence_result r = {.state = GEOFENCE_WARNING, .margin_m = 2};
	struct cue_command cmd;

	cue_init(&c, &CUE_CFG);
	CHECK(cue_update(&c, &r, 5.0, 0).active);
	CHECK(cue_update(&c, &r, 5.0, 19000).active);

	cmd = cue_update(&c, &r, 5.0, 20000);
	CHECK(!cmd.active);
	CHECK(!cue_update(&c, &r, 5.0, 49000).active);
	CHECK(cue_update(&c, &r, 5.0, 50000).active);
}

static void test_cue_outside_times_out(void)
{
	struct cue c;
	struct geofence_result r = {.state = GEOFENCE_OUTSIDE, .margin_m = -3};
	struct cue_command cmd;

	struct geofence_result in = {.state = GEOFENCE_INSIDE, .margin_m = 20};

	cue_init(&c, &CUE_CFG);
	CHECK(!cue_update(&c, &in, 5.0, 0).active);
	cmd = cue_update(&c, &r, 5.0, 1000);
	CHECK(cmd.active && cmd.freq_hz == 1000 && cmd.volume == 4);
	CHECK(cue_update(&c, &r, 5.0, 10000).active);
	CHECK(!cue_update(&c, &r, 5.0, 11000).active);
	CHECK(!cue_update(&c, &r, 5.0, 60000).active);
}

static void test_cue_only_a_crossing(void)
{
	struct geofence gf;
	struct cue c;
	struct cue_command cmd;
	enum geofence_state st;
	int64_t t = 0;

	/* A new boundary that leaves the animal outside: silent, state outside */
	make_square(&gf);
	cue_init(&c, &CUE_CFG);
	for (; t < 60000; t += 1000) {
		cmd = step(&gf, &c, at(50, -20), t, &st);
		CHECK(!cmd.active && st == GEOFENCE_OUTSIDE);
	}

	/* Walks in through the warning zone: still silent, then arms inside */
	CHECK(!step(&gf, &c, at(50, -2), t += 1000, &st).active);
	CHECK(!step(&gf, &c, at(50, 2), t += 1000, &st).active && st == GEOFENCE_WARNING);
	CHECK(!step(&gf, &c, at(50, 4), t += 1000, &st).active && st == GEOFENCE_WARNING);
	CHECK(!c.armed);
	CHECK(!step(&gf, &c, at(50, 20), t += 1000, &st).active && st == GEOFENCE_INSIDE);
	CHECK(c.armed);

	/* Armed: the warning zone cues, and crossing out cues for 10 s */
	cmd = step(&gf, &c, at(50, 3), t += 1000, &st);
	CHECK(cmd.active && cmd.freq_hz == CUE_CFG.warn_freq_hz);
	cmd = step(&gf, &c, at(50, -1), t += 1000, &st);
	CHECK(cmd.active && cmd.freq_hz == CUE_CFG.outside_freq_hz && st == GEOFENCE_OUTSIDE);
	CHECK(step(&gf, &c, at(50, -3), t + 9000, &st).active);
	CHECK(!step(&gf, &c, at(50, -3), t + 10000, &st).active);
	t += 10000;

	/* Coming back in after the crossing: no warning cues on the way in */
	CHECK(!step(&gf, &c, at(50, 2), t += 1000, &st).active && st == GEOFENCE_WARNING);
	CHECK(!step(&gf, &c, at(50, 4), t += 1000, &st).active);
	/* Then outside again without arming: not a crossing */
	CHECK(!step(&gf, &c, at(50, -2), t += 1000, &st).active);
}

static void test_cue_rearm_on_new_boundary(void)
{
	struct geofence gf;
	struct cue c;
	struct cue_command cmd;
	enum geofence_state st;
	struct geo_point moved[] = {at(0, 30), at(100, 30), at(100, 130), at(0, 130)};

	make_square(&gf);
	cue_init(&c, &CUE_CFG);
	CHECK(!step(&gf, &c, at(50, 50), 0, &st).active && c.armed);

	/* A new boundary puts the animal in its warning zone: cued at once */
	CHECK(geofence_init(&gf, &CFG, moved, 4, 2) == 0);
	cue_rearm(&c);
	CHECK(!c.armed);
	cmd = step(&gf, &c, at(50, 33), 1000, &st);
	CHECK(cmd.active && st == GEOFENCE_WARNING && cmd.freq_hz == CUE_CFG.warn_freq_hz);

	/* A new boundary that leaves it outside: no crossing, no cue */
	struct geo_point away[] = {at(0, 60), at(100, 60), at(100, 160), at(0, 160)};

	CHECK(geofence_init(&gf, &CFG, away, 4, 3) == 0);
	cue_rearm(&c);
	CHECK(!step(&gf, &c, at(50, 33), 2000, &st).active && st == GEOFENCE_OUTSIDE);
	CHECK(!step(&gf, &c, at(50, 40), 3000, &st).active);
}

/* ---- Protocol v1 ---- */

static bool take(struct cue *c, struct episode *e)
{
	bool got = cue_take_episode(c, e);
	struct episode more;

	/* Exactly one */
	CHECK(got && !cue_take_episode(c, &more));
	return got;
}

static void test_cues_carry_their_kind(void)
{
	struct geofence gf;
	struct cue c;
	struct cue_command cmd;
	enum geofence_state st;

	make_square(&gf);
	cue_init(&c, &CUE_CFG);
	step(&gf, &c, at(50, 50), 0, &st);
	cmd = step(&gf, &c, at(50, 3), 1000, &st);
	CHECK(cmd.kind == CUE_WARN);
	cmd = step(&gf, &c, at(50, -2), 2000, &st);
	CHECK(cmd.kind == CUE_OUTSIDE);
	cmd = step(&gf, &c, at(50, -2), 30000, &st);
	CHECK(!cmd.active && cmd.kind == CUE_NONE);
	CHECK(strcmp(cue_kind_str(CUE_OUTSIDE), "outside") == 0);
	CHECK(strcmp(episode_outcome_str(EPISODE_BOUNDARY_CHANGED), "boundary_changed") == 0);
}

static void test_episode_turned_back(void)
{
	struct geofence gf;
	struct cue c;
	struct episode e;
	enum geofence_state st;

	make_square(&gf);
	cue_init(&c, &CUE_CFG);
	step(&gf, &c, at(50, 50), 0, &st);
	step(&gf, &c, at(50, 4), 1000, &st);
	step(&gf, &c, at(50, 1.5), 2000, &st);
	step(&gf, &c, at(50, 3), 3000, &st);
	CHECK(!cue_take_episode(&c, &e)); /* Still running */
	step(&gf, &c, at(50, 20), 4000, &st);
	CHECK(take(&c, &e));
	CHECK(e.start == 1000 && e.end == 4000 && e.cues == 3 && e.ring == 0 &&
	      e.outcome == EPISODE_TURNED_BACK);
	CHECK(e.max_level == 3);
	CHECK_NEAR(e.min_margin_m, 1.5, 0.05);
}

static void test_episode_crossed(void)
{
	struct geofence gf;
	struct cue c;
	struct episode e;
	struct cue_command cmd;
	enum geofence_state st;

	make_square(&gf);
	cue_init(&c, &CUE_CFG);
	step(&gf, &c, at(50, 50), 0, &st);
	step(&gf, &c, at(50, 2), 1000, &st);
	cmd = step(&gf, &c, at(50, -1.5), 2000, &st);
	CHECK(cmd.kind == CUE_OUTSIDE); /* The crossing is cued */
	CHECK(take(&c, &e));
	CHECK(e.cues == 1 && e.outcome == EPISODE_CROSSED && e.end == 2000);
	CHECK_NEAR(e.min_margin_m, -1.5, 0.05);
	/* The outside tone that follows is not a new episode */
	step(&gf, &c, at(50, -3), 3000, &st);
	CHECK(!cue_take_episode(&c, &e));
}

static void test_episode_rest(void)
{
	struct geofence gf;
	struct cue c;
	struct episode e;
	enum geofence_state st;

	make_square(&gf);
	cue_init(&c, &CUE_CFG);
	step(&gf, &c, at(50, 50), 0, &st);
	for (int64_t t = 1000; t <= 21000; t += 1000) {
		step(&gf, &c, at(50, 2.5), t, &st);
	}
	CHECK(take(&c, &e));
	CHECK(e.start == 1000 && e.end == 21000 && e.cues == 20 && e.outcome == EPISODE_REST);
	/* Silent while resting; cueing again after it starts a new episode */
	CHECK(!step(&gf, &c, at(50, 2.5), 30000, &st).active);
	CHECK(!step(&gf, &c, at(50, 2.5), 50000, &st).active);
	CHECK(!cue_take_episode(&c, &e));
	CHECK(step(&gf, &c, at(50, 2.5), 52000, &st).active);
	step(&gf, &c, at(50, 30), 53000, &st);
	CHECK(take(&c, &e) && e.outcome == EPISODE_TURNED_BACK);
}

static void test_episode_boundary_changed(void)
{
	struct geofence gf;
	struct cue c;
	struct episode e;
	enum geofence_state st;
	struct geo_point moved[] = {at(0, 30), at(100, 30), at(100, 130), at(0, 130)};

	make_square(&gf);
	cue_init(&c, &CUE_CFG);
	step(&gf, &c, at(50, 50), 0, &st);
	step(&gf, &c, at(50, 3), 1000, &st);
	CHECK(geofence_init(&gf, &CFG, moved, 4, 2) == 0);
	cue_rearm_at(&c, 1500);
	CHECK(take(&c, &e) && e.end == 1500 && e.outcome == EPISODE_BOUNDARY_CHANGED);
	/* cue_rearm() without a time ends one at the last fix */
	step(&gf, &c, at(50, 33), 2000, &st);
	cue_rearm(&c);
	CHECK(take(&c, &e) && e.start == 2000 && e.end == 2000 &&
	      e.outcome == EPISODE_BOUNDARY_CHANGED);
}

static void test_track_mode_is_silent(void)
{
	struct geofence gf;
	struct cue c;
	struct episode e;
	enum geofence_state st, states[7];
	const double n[] = {50, 3, 1, -2, -5, 3, 50};

	make_square(&gf);
	cue_init(&c, &CUE_CFG);
	cue_set_mode(&c, CUE_MODE_TRACK);
	for (int k = 0; k < 7; k++) {
		struct cue_command cmd = step(&gf, &c, at(50, n[k]), 1000 * k, &st);

		CHECK(!cmd.active && cmd.volume == 0 && cmd.kind == CUE_NONE); /* No sound */
		states[k] = st;
	}
	CHECK(!cue_take_episode(&c, &e)); /* No episodes */
	CHECK(states[3] == GEOFENCE_OUTSIDE); /* The fence still runs */
	/* Back to audio: armed by the last inside fix, so it cues again */
	cue_set_mode(&c, CUE_MODE_AUDIO);
	CHECK(step(&gf, &c, at(50, 3), 10000, &st).active);
}

static void test_walking_into_a_hole_is_a_crossing(void)
{
	const double r[][4] = {{0, 0, 100, 100}, {40, 40, 20, 20}};
	struct geofence gf;
	struct cue c;
	struct episode e;
	struct cue_command cmd;
	enum geofence_state st;

	CHECK(rect_fence(&gf, r, 2, 1) == 0);
	cue_init(&c, &CUE_CFG);
	step(&gf, &c, at(50, 20), 0, &st);
	cmd = step(&gf, &c, at(50, 37), 1000, &st);
	CHECK(cmd.kind == CUE_WARN); /* The warning zone runs along the hole */
	cmd = step(&gf, &c, at(50, 42), 2000, &st);
	CHECK(cmd.kind == CUE_OUTSIDE && st == GEOFENCE_OUTSIDE);
	CHECK(take(&c, &e) && e.ring == 1 && e.outcome == EPISODE_CROSSED);
	/* Outside tone for up to 10 s, then silence in the hole */
	CHECK(step(&gf, &c, at(50, 50), 11000, &st).active);
	CHECK(!step(&gf, &c, at(50, 50), 12000, &st).active && st == GEOFENCE_OUTSIDE);
}

static void test_a_hole_drawn_on_an_animal_stays_silent(void)
{
	const double plain[][4] = {{0, 0, 100, 100}};
	const double holed[][4] = {{0, 0, 100, 100}, {40, 40, 20, 20}};
	struct geofence gf;
	struct cue c;
	enum geofence_state st;
	int64_t t = 1000;
	const double walk[] = {50, 45, 41, 38, 36};

	CHECK(rect_fence(&gf, plain, 1, 1) == 0);
	cue_init(&c, &CUE_CFG);
	step(&gf, &c, at(50, 50), 0, &st);
	CHECK(c.armed);

	/* A new boundary with a hole on top of the animal */
	CHECK(rect_fence(&gf, holed, 2, 2) == 0);
	cue_rearm_at(&c, 500);
	for (int k = 0; k < 5; k++, t += 1000) {
		CHECK(!step(&gf, &c, at(50, walk[k]), t, &st).active); /* Silent while it walks out */
	}
	/* Clear of the warning zone: armed again */
	step(&gf, &c, at(50, 25), t, &st);
	CHECK(c.armed);
}

int main(void)
{
	test_cue_volume_ramps();
	test_cue_rest_after_max_active();
	test_cue_outside_times_out();
	test_cue_only_a_crossing();
	test_cue_rearm_on_new_boundary();
	test_cues_carry_their_kind();
	test_episode_turned_back();
	test_episode_crossed();
	test_episode_rest();
	test_episode_boundary_changed();
	test_track_mode_is_silent();
	test_walking_into_a_hole_is_a_crossing();
	test_a_hole_drawn_on_an_animal_stays_silent();
	return test_done("cue");
}
