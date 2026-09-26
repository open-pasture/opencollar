/* Host tests for the geofence and cue logic. Run: make -C tests/host */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "../../src/cue.h"
#include "../../src/geofence.h"

static int failures;

#define CHECK(cond)                                                                    \
	do {                                                                           \
		if (!(cond)) {                                                         \
			printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);         \
			failures++;                                                    \
		}                                                                      \
	} while (0)

#define CHECK_NEAR(a, b, tol) CHECK(fabs((a) - (b)) <= (tol))

/* Origin near Nashville, TN */
static const double LAT0 = 36.1627;
static const double LON0 = -86.7816;

/* Point offset from the origin by east/north metres */
static struct geo_point at(double east_m, double north_m)
{
	const double m_per_deg_lat = 6371008.8 * 3.14159265358979323846 / 180.0;
	const double m_per_deg_lon = m_per_deg_lat * cos(LAT0 * 3.14159265358979323846 / 180.0);

	return (struct geo_point){
		.lat = LAT0 + north_m / m_per_deg_lat,
		.lon = LON0 + east_m / m_per_deg_lon,
	};
}

static const struct geofence_config CFG = {
	.warn_m = 5.0,
	.hysteresis_m = 1.0,
	.max_accuracy_m = 10.0,
};

/* 100 m square */
static void make_square(struct geofence *gf)
{
	struct geo_point sq[] = {at(0, 0), at(100, 0), at(100, 100), at(0, 100)};

	CHECK(geofence_init(gf, &CFG, sq, 4, 1) == 0);
}

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

static const struct cue_config CUE_CFG = {
	.warn_freq_hz = 2730,
	.outside_freq_hz = 1000,
	.beep_ms = 300,
	.max_active_ms = 20000,
	.rest_ms = 30000,
	.outside_max_ms = 10000,
};

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

	cue_init(&c, &CUE_CFG);
	cmd = cue_update(&c, &r, 5.0, 0);
	CHECK(cmd.active && cmd.freq_hz == 1000 && cmd.volume == 4);
	CHECK(cue_update(&c, &r, 5.0, 9000).active);
	CHECK(!cue_update(&c, &r, 5.0, 10000).active);
	CHECK(!cue_update(&c, &r, 5.0, 60000).active);
}

int main(void)
{
	test_margin();
	test_concave();
	test_invalid();
	test_states_and_hysteresis();
	test_degraded_fix_holds_state();
	test_cue_volume_ramps();
	test_cue_rest_after_max_active();
	test_cue_outside_times_out();

	if (failures) {
		printf("%d failure(s)\n", failures);
		return EXIT_FAILURE;
	}
	printf("all tests passed\n");
	return EXIT_SUCCESS;
}
