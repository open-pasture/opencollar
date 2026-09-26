#include "geofence.h"

#include <math.h>
#include <string.h>

#define EARTH_RADIUS_M 6371008.8
#define DEG_TO_RAD (3.14159265358979323846 / 180.0)
#define M_PER_DEG_LAT (EARTH_RADIUS_M * DEG_TO_RAD)

static void project(const struct geofence *gf, struct geo_point p, double *x, double *y)
{
	*x = (p.lon - gf->lon0) * gf->m_per_deg_lon;
	*y = (p.lat - gf->lat0) * M_PER_DEG_LAT;
}

int geofence_init(struct geofence *gf, const struct geofence_config *cfg,
		  const struct geo_point *vertices, int n, uint32_t version)
{
	if (n < 3 || n > GEOFENCE_MAX_VERTICES) {
		return -1;
	}

	memset(gf, 0, sizeof(*gf));
	gf->cfg = *cfg;
	gf->version = version;
	gf->n = n;
	gf->lat0 = vertices[0].lat;
	gf->lon0 = vertices[0].lon;
	gf->m_per_deg_lon = M_PER_DEG_LAT * cos(gf->lat0 * DEG_TO_RAD);
	gf->state = GEOFENCE_UNKNOWN;

	for (int i = 0; i < n; i++) {
		project(gf, vertices[i], &gf->x[i], &gf->y[i]);
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

double geofence_margin_m(const struct geofence *gf, struct geo_point p)
{
	double px, py;
	bool inside = false;
	double min_d = INFINITY;

	project(gf, p, &px, &py);

	for (int i = 0, j = gf->n - 1; i < gf->n; j = i++) {
		double xi = gf->x[i], yi = gf->y[i];
		double xj = gf->x[j], yj = gf->y[j];

		/* Even-odd ray cast toward +x */
		if ((yi > py) != (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) {
			inside = !inside;
		}

		double d = segment_distance(px, py, xi, yi, xj, yj);
		if (d < min_d) {
			min_d = d;
		}
	}

	return inside ? min_d : -min_d;
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

	r.margin_m = geofence_margin_m(gf, p);
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
