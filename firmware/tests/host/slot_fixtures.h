/* Boundary commands for the slot and store tests, built as slots.json describes them */
#ifndef SLOT_FIXTURES_H
#define SLOT_FIXTURES_H

#include <stdio.h>

#include "../../src/command.h"
#include "../../src/shape.h"
#include "test.h"

/* Ames, Iowa: the vectors' farm */
#define AMES_LON -93.62
#define AMES_LAT 42.03

static inline int32_t fx_e7(double deg)
{
	return (int32_t)llround(deg * 1e7);
}

/* A circle of n vertices, radius r metres, centred (cx, cy) metres from Ames */
static inline void fx_circle(struct shape *s, double cx, double cy, double r, int n)
{
	const double pi = 3.14159265358979323846;
	const double m_lat = 6371008.8 * pi / 180.0;
	const double m_lon = m_lat * cos(AMES_LAT * (pi / 180.0));

	shape_ring_begin(s);
	for (int i = 0; i < n; i++) {
		double a = 2 * pi * i / n;
		double lon = AMES_LON + (cx + r * cos(a)) / m_lon;
		double lat = AMES_LAT + (cy + r * sin(a)) / m_lat;

		shape_vertex(s, fx_e7(lon), fx_e7(lat), true);
	}
	shape_ring_end(s);
}

/*
 * A valid boundary of `total` vertices within `limits`: a 400 m circle, plus
 * 20 m holes of up to hole_vertices each on a 100 m grid (as the vectors'
 * shape_with).
 */
static inline void fx_shape(struct shape *s, int32_t (*buf)[2], int total,
			    const struct collar_limits *limits)
{
	int outer = total < limits->outer ? total : limits->outer;
	int left = total - outer, spot = 0;

	shape_init(s, buf, SHAPE_BUF_VERTICES);
	fx_circle(s, 0, 0, 400, outer);
	while (left > 0 && limits->hole_vertices > 0) {
		int k = left < limits->hole_vertices ? left : limits->hole_vertices;

		if (left - k > 0 && left - k < 3) {
			k -= 3 - (left - k);
		}
		fx_circle(s, -150 + 100 * (spot % 4), -150 + 100 * (spot / 4), 20, k);
		left -= k;
		spot++;
	}
}

/* A verified command as command_parse would leave it */
static inline void fx_command(struct boundary_cmd *cmd, int32_t (*buf)[2], uint32_t version,
			      const char *herd, const char *collar, bool has_effective,
			      int64_t effective_at, int vertices, const struct collar_limits *limits)
{
	char id[32];

	memset(cmd, 0, sizeof(*cmd));
	snprintf(id, sizeof(id), "bnd_v%u", (unsigned)version);
	proto_id_set(&cmd->command_id, id, strlen(id));
	cmd->version = version;
	if (herd) {
		cmd->has_herd = true;
		proto_id_set(&cmd->herd_id, herd, strlen(herd));
	}
	if (collar) {
		cmd->has_collar = true;
		proto_id_set(&cmd->collar_id, collar, strlen(collar));
	}
	cmd->has_effective_at = has_effective;
	cmd->effective_at = effective_at;
	fx_shape(&cmd->shape, buf, vertices, limits);
	CHECK(cmd->shape.total == (uint32_t)vertices);
	CHECK(shape_check(&cmd->shape, limits, 5.0, 1.0, 0.0) == REJECT_NONE);
}

#endif
