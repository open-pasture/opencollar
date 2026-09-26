/*
 * Geofence engine. Plain C, no Zephyr dependencies, so it runs in host tests.
 *
 * The boundary is projected once into a local metric plane (east/north metres
 * around the polygon's first vertex). Every fix is projected the same way and
 * compared against the polygon in metres, using doubles throughout.
 */
#ifndef OPENCOLLAR_GEOFENCE_H
#define OPENCOLLAR_GEOFENCE_H

#include <stdbool.h>
#include <stdint.h>

#define GEOFENCE_MAX_VERTICES 64

struct geo_point {
	double lat;
	double lon;
};

enum geofence_state {
	GEOFENCE_UNKNOWN = 0, /* No usable fix yet */
	GEOFENCE_INSIDE,      /* Inside, clear of the warning zone */
	GEOFENCE_WARNING,     /* Inside, within warn_m of the edge */
	GEOFENCE_OUTSIDE,     /* Outside the polygon */
};

struct geofence_config {
	double warn_m;         /* Width of the warning zone inside the edge */
	double hysteresis_m;   /* Extra margin needed to step back to a calmer state */
	double max_accuracy_m; /* Fixes worse than this don't change state */
};

struct geofence {
	struct geofence_config cfg;
	uint32_t version;
	int n;
	double lat0, lon0, m_per_deg_lon;
	double x[GEOFENCE_MAX_VERTICES];
	double y[GEOFENCE_MAX_VERTICES];
	enum geofence_state state;
};

struct geofence_result {
	enum geofence_state state;
	double margin_m; /* Signed distance to the edge: + inside, - outside */
	bool degraded;   /* Fix accuracy too poor; state held from last good fix */
	bool changed;    /* State differs from the previous result */
};

/* Returns 0 on success, -1 if the polygon is invalid (<3 or too many vertices). */
int geofence_init(struct geofence *gf, const struct geofence_config *cfg,
		  const struct geo_point *vertices, int n, uint32_t version);

/* Signed distance in metres from a point to the boundary: + inside, - outside. */
double geofence_margin_m(const struct geofence *gf, struct geo_point p);

/* Feed a fix. accuracy_m is the receiver's horizontal accuracy estimate. */
struct geofence_result geofence_update(struct geofence *gf, struct geo_point p,
				       double accuracy_m);

const char *geofence_state_str(enum geofence_state s);

#endif
