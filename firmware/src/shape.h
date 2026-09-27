/*
 * Shape rules for boundaries (protocol v1 §3.5). Plain C, host-testable.
 *
 * A boundary arrives as rings of [lon, lat] numbers. The command parser feeds
 * each vertex, already converted exactly to e7 integers (degrees x 1e7), into
 * a struct shape: consecutive duplicates and a closing vertex equal to the
 * first are dropped as it goes, and vertices are stored only while the shape
 * can still be within the limits.
 *
 * shape_check() then applies the rules in order; the first that fails is the
 * rejection code. The order and the math match openpasture's
 * op_geo::shape::check_rings exactly (see protocol/README.md):
 *
 *  1. bad_margins      warn_m or hysteresis_m not finite, or outside 0-1000
 *  2. too_many_holes   more holes than limits.holes
 *  3. out_of_range     |lon| > 180 or |lat| > 90
 *  4. too_few_vertices a ring with fewer than 3 vertices after cleaning
 *  5. too_many_vertices outer ring, a hole, or all rings over the limits
 *  6. self_intersecting two edges of one ring meet (other than neighbours)
 *  7. rings_cross      an edge of one ring meets an edge of another
 *  8. hole_outside     a hole's first vertex is not inside the outer ring
 *  9. holes_overlap    a hole's first vertex is inside another hole
 * 10. zero_area        outer ring under 1 m^2
 * 11. hole_too_small   a hole under 100 m^2
 * 12. hole_too_close   two rings closer than 2 * warn_m + 2 m (+ slack)
 *
 * Rules 6-9 are exact on the e7 integers (int64 orientation tests). Rules
 * 10-12 are single precision, projected about the outer ring's first vertex.
 */
#ifndef OPENCOLLAR_SHAPE_H
#define OPENCOLLAR_SHAPE_H

#include <stdbool.h>
#include <stdint.h>

#include "protocol.h"

/* Outer ring plus 16 holes: the most any limit allows */
#define SHAPE_MAX_RINGS 17
/* Most vertices over all rings */
#define SHAPE_MAX_TOTAL 384
/* Storage a shape needs: the total plus one ring's closing vertex in flight */
#define SHAPE_BUF_VERTICES (SHAPE_MAX_TOTAL + 1)

/* Largest warn_m or hysteresis_m */
#define SHAPE_MAX_MARGIN_M 1000.0

struct shape {
	int32_t (*v)[2]; /* [lon_e7, lat_e7], rings back to back */
	uint16_t cap;
	uint16_t stored;
	uint32_t rings;                /* rings seen */
	uint16_t len[SHAPE_MAX_RINGS]; /* vertices per ring after cleaning */
	uint32_t total;                /* vertices over every ring after cleaning */
	bool out_of_range;
	bool overflow; /* ran out of storage: only when over the vertex limits */

	/* The ring being built */
	uint32_t cur_count;
	uint32_t cur_stored;
	int32_t first[2];
	int32_t last[2];
};

void shape_init(struct shape *s, int32_t (*buf)[2], uint16_t cap);
void shape_ring_begin(struct shape *s);
/* lon_e7/lat_e7 only matter when in_range */
void shape_vertex(struct shape *s, int64_t lon_e7, int64_t lat_e7, bool in_range);
void shape_ring_end(struct shape *s);

/* Holes in the shape (rings - 1) */
static inline uint32_t shape_holes(const struct shape *s)
{
	return s->rings > 0 ? s->rings - 1 : 0;
}

/* First vertex of ring k (valid after a passing shape_check) */
const int32_t (*shape_ring(const struct shape *s, int k))[2];

/* The collar passes slack_m = 0; the server checks with 0.5 */
enum reject_code shape_check(const struct shape *s, const struct collar_limits *limits,
			     double warn_m, double hysteresis_m, double slack_m);

/* 2 * warn_m + 2: least distance between rings */
static inline double shape_min_gap_m(double warn_m)
{
	return 2.0 * warn_m + 2.0;
}

#endif
