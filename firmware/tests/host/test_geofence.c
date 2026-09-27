/* Geofence: the V0 tests (unchanged), holes, nearest ring, geofence.json, timing */
#include <time.h>

#include "../../src/command.h"
#include "json.h"
#include "v0_fixtures.h"

/* ---- V0 tests, as they were in test_main.c ---- */

static void test_margin(void)
{
	struct geofence gf;

	make_square(&gf);
	CHECK_NEAR(geofence_margin_m(&gf, at(50, 50)), 50.0, 0.05);
	CHECK_NEAR(geofence_margin_m(&gf, at(50, 3)), 3.0, 0.05);
	CHECK_NEAR(geofence_margin_m(&gf, at(50, -10)), -10.0, 0.05);
	/* Off a corner: distance is to the vertex, not the extended edge */
	CHECK_NEAR(geofence_margin_m(&gf, at(110, 110)), -sqrt(200.0), 0.05);
}

static void test_concave(void)
{
	/* L shape: the notch at (75,75) is outside */
	struct geo_point l[] = {at(0, 0),    at(100, 0), at(100, 50),
				at(50, 50),  at(50, 100), at(0, 100)};
	struct geofence gf;

	CHECK(geofence_init(&gf, &CFG, l, 6, 1) == 0);
	CHECK(geofence_margin_m(&gf, at(75, 75)) < 0);
	CHECK_NEAR(geofence_margin_m(&gf, at(75, 75)), -25.0, 0.05);
	CHECK(geofence_margin_m(&gf, at(25, 75)) > 0);
}

static void test_invalid(void)
{
	struct geofence gf;
	struct geo_point two[] = {at(0, 0), at(1, 1)};

	CHECK(geofence_init(&gf, &CFG, two, 2, 1) == -1);
}

static void test_states_and_hysteresis(void)
{
	struct geofence gf;
	struct geofence_result r;

	make_square(&gf);
	CHECK(gf.state == GEOFENCE_UNKNOWN);

	r = geofence_update(&gf, at(50, 50), 3);
	CHECK(r.state == GEOFENCE_INSIDE && r.changed);

	r = geofence_update(&gf, at(50, 4), 3);
	CHECK(r.state == GEOFENCE_WARNING && r.changed);

	/* Just past warn_m but inside the hysteresis band: stay in warning */
	r = geofence_update(&gf, at(50, 5.5), 3);
	CHECK(r.state == GEOFENCE_WARNING && !r.changed);

	r = geofence_update(&gf, at(50, 6.5), 3);
	CHECK(r.state == GEOFENCE_INSIDE);

	r = geofence_update(&gf, at(50, -1), 3);
	CHECK(r.state == GEOFENCE_OUTSIDE);

	/* Barely back inside: still outside until past the hysteresis margin */
	r = geofence_update(&gf, at(50, 0.5), 3);
	CHECK(r.state == GEOFENCE_OUTSIDE);

	r = geofence_update(&gf, at(50, 2), 3);
	CHECK(r.state == GEOFENCE_WARNING);
}

static void test_degraded_fix_holds_state(void)
{
	struct geofence gf;
	struct geofence_result r;

	make_square(&gf);
	geofence_update(&gf, at(50, 50), 3);

	r = geofence_update(&gf, at(50, -20), 25);
	CHECK(r.degraded);
	CHECK(r.state == GEOFENCE_INSIDE);
	CHECK(r.margin_m < 0);
}

/* ---- Holes (protocol v1 §3.6) ---- */

static void test_margins_around_and_inside_a_hole(void)
{
	/* 100 m square with a 20 m hole in the middle */
	const double r[][4] = {{0, 0, 100, 100}, {40, 40, 20, 20}};
	struct geofence gf;
	int ring;

	CHECK(rect_fence(&gf, r, 2, 1) == 0);
	CHECK(gf.rings == 2 && gf.n == 8);
	/* In the hole: outside, 10 m from its edge */
	CHECK_NEAR(geofence_measure(&gf, at(50, 50), &ring), -10.0, 0.05);
	CHECK(ring == 1);
	/* Between the hole and the edge: nearer the hole */
	CHECK_NEAR(geofence_measure(&gf, at(50, 30), &ring), 10.0, 0.05);
	CHECK(ring == 1);
	/* Nearer the outer edge */
	CHECK_NEAR(geofence_measure(&gf, at(50, 5), &ring), 5.0, 0.05);
	CHECK(ring == 0);
	/* Off the hole's corner */
	CHECK_NEAR(geofence_measure(&gf, at(35, 35), &ring), sqrt(50.0), 0.05);
	CHECK(ring == 1);
	/* Outside the outer ring */
	CHECK_NEAR(geofence_measure(&gf, at(50, -3), &ring), -3.0, 0.05);
	CHECK(ring == 0);
}

static void test_warning_zone_along_a_hole(void)
{
	const double r[][4] = {{0, 0, 100, 100}, {40, 40, 20, 20}};
	struct geofence gf;
	struct geofence_result res;

	CHECK(rect_fence(&gf, r, 2, 1) == 0);
	res = geofence_update(&gf, at(50, 20), 3);
	CHECK(res.state == GEOFENCE_INSIDE);
	res = geofence_update(&gf, at(50, 37), 3);
	CHECK(res.state == GEOFENCE_WARNING && res.nearest_ring == 1);
	res = geofence_update(&gf, at(50, 42), 3);
	CHECK(res.state == GEOFENCE_OUTSIDE && res.nearest_ring == 1);
}

static void test_concave_hole(void)
{
	/* An L-shaped hole: its notch at (70,70) is fenced ground */
	struct geo_point l[] = {at(40, 40), at(80, 40), at(80, 60), at(60, 60), at(60, 80), at(40, 80)};
	struct geo_point outer[] = {at(0, 0), at(100, 0), at(100, 100), at(0, 100)};
	int32_t v[10][2];
	uint16_t len[2] = {4, 6};
	struct geofence gf;
	int ring;

	for (int i = 0; i < 4; i++) {
		e7_of(outer[i], v[i]);
	}
	for (int i = 0; i < 6; i++) {
		e7_of(l[i], v[4 + i]);
	}
	CHECK(geofence_init_e7(&gf, &CFG, (const int32_t(*)[2])v, len, 2, 1) == 0);
	CHECK_NEAR(geofence_measure(&gf, at(70, 70), &ring), 10.0, 0.05);
	CHECK(ring == 1);
	CHECK_NEAR(geofence_measure(&gf, at(50, 70), &ring), -10.0, 0.05);
	CHECK(ring == 1);
}

static void test_nearest_ring(void)
{
	const double r[][4] = {{0, 0, 100, 100}, {10, 40, 20, 20}, {70, 40, 20, 20}};
	struct geofence gf;
	int ring;

	CHECK(rect_fence(&gf, r, 3, 1) == 0);
	CHECK_NEAR(geofence_measure(&gf, at(66, 50), &ring), 4.0, 0.05);
	CHECK(ring == 2);
	CHECK_NEAR(geofence_measure(&gf, at(34, 50), &ring), 4.0, 0.05);
	CHECK(ring == 1);
	CHECK_NEAR(geofence_measure(&gf, at(50, 97), &ring), 3.0, 0.05);
	CHECK(ring == 0);
	CHECK_NEAR(geofence_measure(&gf, at(80, 50), &ring), -10.0, 0.05);
	CHECK(ring == 2);
}

static void test_init_e7_rejects(void)
{
	struct geofence gf;
	int32_t v[3][2] = {{0, 0}, {10, 0}, {10, 10}};
	uint16_t two[1] = {2}, many[1] = {GEOFENCE_MAX_VERTICES + 1};

	CHECK(geofence_init_e7(&gf, &CFG, (const int32_t(*)[2])v, two, 1, 1) == -1);
	CHECK(geofence_init_e7(&gf, &CFG, (const int32_t(*)[2])v, many, 1, 1) == -1);
	CHECK(geofence_init_e7(&gf, &CFG, (const int32_t(*)[2])v, two, 0, 1) == -1);
}

/* ---- geofence.json ---- */

static bool ring_e7(const struct jval *ring, int32_t (*out)[2], uint16_t *len)
{
	for (size_t i = 0; i < ring->n; i++) {
		const struct jval *p = &ring->items[i];
		int64_t lon, lat;
		bool a, b;

		if (!wire_e7(p->items[0].raw, p->items[0].raw_len, 1800000000, &lon, &a) ||
		    !wire_e7(p->items[1].raw, p->items[1].raw_len, 900000000, &lat, &b) || !a || !b) {
			return false;
		}
		out[i][0] = (int32_t)lon;
		out[i][1] = (int32_t)lat;
	}
	*len = (uint16_t)ring->n;
	return true;
}

static int test_vectors(void)
{
	struct jval *f = json_load(VECTORS "/geofence.json");
	const struct jval *cases = jget(f, "cases");
	double tol = jnum(f, "tolerance_m");
	int n = 0;

	CHECK(tol > 0 && tol <= 0.001);
	for (size_t c = 0; c < cases->n; c++) {
		const struct jval *k = &cases->items[c];
		const char *name = jstr(k, "name");
		const struct jval *holes = jget(k, "holes");
		const struct jval *pt = jget(k, "point");
		int32_t v[GEOFENCE_MAX_VERTICES][2];
		uint16_t len[GEOFENCE_MAX_RINGS];
		int total = 0, rings = 1, ring = -1;
		struct geofence gf;
		bool ok = ring_e7(jget(k, "boundary"), v, &len[0]);

		total = len[0];
		for (size_t h = 0; ok && holes && h < holes->n; h++) {
			ok = ring_e7(&holes->items[h], &v[total], &len[rings]);
			total += len[rings++];
		}
		CHECK_CASE(ok, name, "rings read");
		CHECK_CASE(geofence_init_e7(&gf, &CFG, (const int32_t(*)[2])v, len, rings, 1) == 0,
			   name, "fence built");

		struct geo_point p = {.lat = pt->items[1].num, .lon = pt->items[0].num};
		double margin = geofence_measure(&gf, p, &ring);
		double want = jnum(k, "margin_m");

		CHECK_CASE(fabs(margin - want) <= tol, name, "margin %.6f, want %.6f", margin, want);
		CHECK_CASE((margin > 0) == jbool(k, "inside"), name, "inside");
		CHECK_CASE(ring == (int)jnum(k, "nearest_ring"), name, "nearest ring %d", ring);
		n++;
	}
	CHECK(n >= 20);
	return n;
}

/* ---- 384 vertices: time per fix ---- */

static void test_timing_384(void)
{
	int32_t v[GEOFENCE_MAX_VERTICES][2];
	uint16_t len[9];
	int n = 0;
	struct geofence gf;
	struct timespec t0, t1;
	volatile double sink = 0;
	const int fixes = 200000;

	/* A 400 m circle of 128 vertices and 8 holes of 32 */
	for (int i = 0; i < 128; i++) {
		double a = 2 * 3.14159265358979323846 * i / 128;

		e7_of(at(400 * cos(a), 400 * sin(a)), v[n++]);
	}
	len[0] = 128;
	for (int h = 0; h < 8; h++) {
		double cx = -150 + 100 * (h % 4), cy = -150 + 100 * (h / 4);

		for (int i = 0; i < 32; i++) {
			double a = 2 * 3.14159265358979323846 * i / 32;

			e7_of(at(cx + 20 * cos(a), cy + 20 * sin(a)), v[n++]);
		}
		len[1 + h] = 32;
	}
	CHECK(n == 384);
	CHECK(geofence_init_e7(&gf, &CFG, (const int32_t(*)[2])v, len, 9, 1) == 0);

	clock_gettime(CLOCK_MONOTONIC, &t0);
	for (int i = 0; i < fixes; i++) {
		/* Worst case for the box shortcut: points close to the holes */
		sink += geofence_margin_m(&gf, at(-150 + (i % 400), -150 + (i % 97)));
	}
	clock_gettime(CLOCK_MONOTONIC, &t1);

	double ns = ((double)(t1.tv_sec - t0.tv_sec) * 1e9 + (double)(t1.tv_nsec - t0.tv_nsec)) /
		    fixes;

	printf("geofence: 384 vertices, 9 rings: %.0f ns per fix on this host (%d fixes)\n", ns,
	       fixes);
	(void)sink;
}

int main(void)
{
	int n;

	test_margin();
	test_concave();
	test_invalid();
	test_states_and_hysteresis();
	test_degraded_fix_holds_state();
	test_margins_around_and_inside_a_hole();
	test_warning_zone_along_a_hole();
	test_concave_hole();
	test_nearest_ring();
	test_init_e7_rejects();
	n = test_vectors();
	test_timing_384();
	printf("geofence.json: %d cases\n", n);
	return test_done("geofence");
}
