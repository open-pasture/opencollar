/* Fixtures of the V0 geofence and cue tests, shared by test_geofence.c and test_cue.c */
#ifndef V0_FIXTURES_H
#define V0_FIXTURES_H

#include "../../src/cue.h"
#include "../../src/geofence.h"
#include "test.h"

/* Origin near Nashville, TN */
__attribute__((unused)) static const double LAT0 = 36.1627;
__attribute__((unused)) static const double LON0 = -86.7816;

/* Point offset from the origin by east/north metres */
__attribute__((unused)) static struct geo_point at(double east_m, double north_m)
{
	const double m_per_deg_lat = 6371008.8 * 3.14159265358979323846 / 180.0;
	const double m_per_deg_lon = m_per_deg_lat * cos(LAT0 * 3.14159265358979323846 / 180.0);

	return (struct geo_point){
		.lat = LAT0 + north_m / m_per_deg_lat,
		.lon = LON0 + east_m / m_per_deg_lon,
	};
}

__attribute__((unused)) static const struct geofence_config CFG = {
	.warn_m = 5.0,
	.hysteresis_m = 1.0,
	.max_accuracy_m = 10.0,
};

/* 100 m square */
static inline void make_square(struct geofence *gf)
{
	struct geo_point sq[] = {at(0, 0), at(100, 0), at(100, 100), at(0, 100)};

	CHECK(geofence_init(gf, &CFG, sq, 4, 1) == 0);
}

__attribute__((unused)) static const struct cue_config CUE_CFG = {
	.warn_freq_hz = 2730,
	.outside_freq_hz = 1000,
	.beep_ms = 300,
	.max_active_ms = 20000,
	.rest_ms = 30000,
	.outside_max_ms = 10000,
};

/* Feed a fix through the fence and the cue, as main.c does */
static inline struct cue_command step(struct geofence *gf, struct cue *c, struct geo_point p,
				      int64_t now_ms, enum geofence_state *state)
{
	struct geofence_result r = geofence_update(gf, p, 3);

	*state = r.state;
	return cue_update(c, &r, CFG.warn_m, now_ms);
}

/* A point as e7 integers */
static inline void e7_of(struct geo_point p, int32_t out[2])
{
	out[0] = (int32_t)llround(p.lon * 1e7);
	out[1] = (int32_t)llround(p.lat * 1e7);
}

/* A fence of axis-aligned rectangles in metres from the origin: the first is
 * the outer ring, the rest holes. r[i] = {x, y, w, h}. */
static inline int rect_fence(struct geofence *gf, const double (*r)[4], int n, uint32_t version)
{
	int32_t v[4 * 17][2];
	uint16_t len[17];

	for (int k = 0; k < n; k++) {
		double x = r[k][0], y = r[k][1], w = r[k][2], h = r[k][3];

		e7_of(at(x, y), v[4 * k]);
		e7_of(at(x + w, y), v[4 * k + 1]);
		e7_of(at(x + w, y + h), v[4 * k + 2]);
		e7_of(at(x, y + h), v[4 * k + 3]);
		len[k] = 4;
	}
	return geofence_init_e7(gf, &CFG, (const int32_t(*)[2])v, len, n, version);
}

#endif
