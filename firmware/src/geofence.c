#include "geofence.h"

#include <math.h>
#include <string.h>

#define EARTH_RADIUS_M 6371008.8
#define PI_D 3.14159265358979323846
#define M_PER_DEG_LAT (EARTH_RADIUS_M * PI_D / 180.0)

static void project(const struct geofence *gf, struct geo_point p, double *x, double *y)
{
	*x = (p.lon - gf->lon0) * gf->m_per_deg_lon;
	*y = (p.lat - gf->lat0) * M_PER_DEG_LAT;
}

static void start(struct geofence *gf, const struct geofence_config *cfg, struct geo_point origin,
		  uint32_t version)
{
	memset(gf, 0, sizeof(*gf));
	gf->cfg = *cfg;
	gf->version = version;
	gf->lat0 = origin.lat;
	gf->lon0 = origin.lon;
	gf->m_per_deg_lon = M_PER_DEG_LAT * cos(gf->lat0 * (PI_D / 180.0));
	gf->state = GEOFENCE_UNKNOWN;
}

/* Append one projected point to the ring being built */
static void add(struct geofence *gf, struct geo_point p)
{
	int k = gf->rings - 1;
	int i = gf->n++;
	double *b = gf->bbox[k];

	project(gf, p, &gf->x[i], &gf->y[i]);
	if (gf->ring_len[k]++ == 0) {
		b[0] = b[2] = gf->x[i];
		b[1] = b[3] = gf->y[i];
	} else {
		b[0] = fmin(b[0], gf->x[i]);
		b[1] = fmin(b[1], gf->y[i]);
		b[2] = fmax(b[2], gf->x[i]);
		b[3] = fmax(b[3], gf->y[i]);
	}
}

static void begin_ring(struct geofence *gf)
{
	gf->ring_start[gf->rings] = (uint16_t)gf->n;
	gf->ring_len[gf->rings] = 0;
	gf->rings++;
}

int geofence_init(struct geofence *gf, const struct geofence_config *cfg,
		  const struct geo_point *vertices, int n, uint32_t version)
{
	if (n < 3 || n > GEOFENCE_MAX_VERTICES) {
		return -1;
	}

	start(gf, cfg, vertices[0], version);
	begin_ring(gf);
	for (int i = 0; i < n; i++) {
		add(gf, vertices[i]);
	}
	return 0;
}

static struct geo_point from_e7(const int32_t v[2])
{
	return (struct geo_point){.lat = (double)v[1] / 1e7, .lon = (double)v[0] / 1e7};
}

int geofence_init_e7(struct geofence *gf, const struct geofence_config *cfg,
		     const int32_t (*vertices)[2], const uint16_t *ring_len, int rings,
		     uint32_t version)
{
	int total = 0;

	if (rings < 1 || rings > GEOFENCE_MAX_RINGS) {
		return -1;
	}
	for (int k = 0; k < rings; k++) {
		if (ring_len[k] < 3) {
			return -1;
		}
		total += ring_len[k];
	}
	if (total > GEOFENCE_MAX_VERTICES) {
		return -1;
	}

	start(gf, cfg, from_e7(vertices[0]), version);
	for (int k = 0, i = 0; k < rings; k++) {
		begin_ring(gf);
		for (int j = 0; j < ring_len[k]; j++, i++) {
			add(gf, from_e7(vertices[i]));
		}
	}
	return 0;
}

/* Distance from (px,py) to segment (ax,ay)-(bx,by), clamped to the segment ends. */
static double segment_distance(double px, double py, double ax, double ay, double bx, double by)
{
	double dx = bx - ax;
	double dy = by - ay;
	double len2 = dx * dx + dy * dy;
	double t = 0.0;

	if (len2 > 0.0) {
		t = ((px - ax) * dx + (py - ay) * dy) / len2;
		if (t < 0.0) {
			t = 0.0;
		} else if (t > 1.0) {
			t = 1.0;
		}
	}

	double cx = ax + t * dx - px;
	double cy = ay + t * dy - py;

	return sqrt(cx * cx + cy * cy);
}

/* Even-odd ray cast toward +x and the least distance to one ring's edges */
static bool ring_test(const struct geofence *gf, int k, double px, double py, double *min_d)
{
	const double *x = &gf->x[gf->ring_start[k]];
	const double *y = &gf->y[gf->ring_start[k]];
	int n = gf->ring_len[k];
	bool inside = false;
	double best = INFINITY;

	for (int i = 0, j = n - 1; i < n; j = i++) {
		double xi = x[i], yi = y[i];
		double xj = x[j], yj = y[j];

		if ((yi > py) != (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) {
			inside = !inside;
		}

		double d = segment_distance(px, py, xi, yi, xj, yj);

		if (d < best) {
			best = d;
		}
	}
	*min_d = best;
	return inside;
}

double geofence_measure(const struct geofence *gf, struct geo_point p, int *nearest_ring)
{
	double px, py, min_d;
	int nearest = 0;

	project(gf, p, &px, &py);

	bool inside = ring_test(gf, 0, px, py, &min_d);

	for (int k = 1; k < gf->rings; k++) {
		const double *b = gf->bbox[k];
		double dx = fmax(fmax(b[0] - px, px - b[2]), 0.0);
		double dy = fmax(fmax(b[1] - py, py - b[3]), 0.0);

		/* A hole whose box is farther than the nearest edge so far can't be
		 * nearer, and a point outside its box isn't in it */
		if (hypot(dx, dy) > min_d) {
			continue;
		}

		double d;

		if (ring_test(gf, k, px, py, &d)) {
			inside = false;
		}
		if (d < min_d) {
			min_d = d;
			nearest = k;
		}
	}

	if (nearest_ring) {
		*nearest_ring = nearest;
	}
	return inside ? min_d : -min_d;
}

double geofence_margin_m(const struct geofence *gf, struct geo_point p)
{
	return geofence_measure(gf, p, NULL);
}

static enum geofence_state classify(const struct geofence *gf, double margin)
{
	const double warn = gf->cfg.warn_m;
	const double hyst = gf->cfg.hysteresis_m;

	switch (gf->state) {
	case GEOFENCE_OUTSIDE:
		/* Must come back past the edge by the hysteresis margin */
		if (margin < hyst) {
			return GEOFENCE_OUTSIDE;
		}
		return margin < warn + hyst ? GEOFENCE_WARNING : GEOFENCE_INSIDE;
	case GEOFENCE_WARNING:
		if (margin < 0.0) {
			return GEOFENCE_OUTSIDE;
		}
		return margin < warn + hyst ? GEOFENCE_WARNING : GEOFENCE_INSIDE;
	default:
		if (margin < 0.0) {
			return GEOFENCE_OUTSIDE;
		}
		return margin < warn ? GEOFENCE_WARNING : GEOFENCE_INSIDE;
	}
}

struct geofence_result geofence_update(struct geofence *gf, struct geo_point p,
				       double accuracy_m)
{
	struct geofence_result r = {0};
	enum geofence_state prev = gf->state;

	r.margin_m = geofence_measure(gf, p, &r.nearest_ring);
	r.degraded = accuracy_m > gf->cfg.max_accuracy_m;

	if (!r.degraded) {
		gf->state = classify(gf, r.margin_m);
	}

	r.state = gf->state;
	r.changed = gf->state != prev;

	return r;
}

const char *geofence_state_str(enum geofence_state s)
{
	switch (s) {
	case GEOFENCE_INSIDE:
		return "inside";
	case GEOFENCE_WARNING:
		return "warning";
	case GEOFENCE_OUTSIDE:
		return "outside";
	default:
		return "unknown";
	}
}
