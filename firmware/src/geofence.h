/*
 * Geofence engine. Plain C, no Zephyr dependencies, so it runs in host tests.
 *
 * The boundary is an outer ring and up to 16 holes (protocol v1 §3.6). Every
 * ring is projected once into a local metric plane (east/north metres around
 * the outer ring's first vertex). Every fix is projected the same way and
 * compared against the rings in metres, using doubles throughout: inside
 * means inside the outer ring and outside every hole (even-odd per ring), and
 * the margin is the distance to the nearest edge of any ring, positive
 * inside. The warning zone therefore runs along hole edges too.
 */
#ifndef OPENCOLLAR_GEOFENCE_H
#define OPENCOLLAR_GEOFENCE_H

#include <stdbool.h>
#include <stdint.h>

/* Most vertices over every ring, and most rings (outer + 16 holes) */
#define GEOFENCE_MAX_VERTICES 384
#define GEOFENCE_MAX_RINGS 17

struct geo_point {
	double lat;
	double lon;
};

enum geofence_state {
	GEOFENCE_UNKNOWN = 0, /* No usable fix yet */
	GEOFENCE_INSIDE,      /* Inside, clear of the warning zone */
	GEOFENCE_WARNING,     /* Inside, within warn_m of an edge */
	GEOFENCE_OUTSIDE,     /* Outside the outer ring, or inside a hole */
};

struct geofence_config {
	double warn_m;         /* Width of the warning zone inside the edge */
	double hysteresis_m;   /* Extra margin needed to step back to a calmer state */
	double max_accuracy_m; /* Fixes worse than this don't change state */
};

struct geofence {
	struct geofence_config cfg;
	uint32_t version;
	int rings;
	int n; /* vertices over every ring */
	uint16_t ring_start[GEOFENCE_MAX_RINGS];
	uint16_t ring_len[GEOFENCE_MAX_RINGS];
	double bbox[GEOFENCE_MAX_RINGS][4]; /* min x, min y, max x, max y, metres */
	double lat0, lon0, m_per_deg_lon;
	double x[GEOFENCE_MAX_VERTICES];
	double y[GEOFENCE_MAX_VERTICES];
	enum geofence_state state;
};

struct geofence_result {
	enum geofence_state state;
	double margin_m;  /* Signed distance to the nearest edge: + inside, - outside */
	bool degraded;    /* Fix accuracy too poor; state held from last good fix */
	bool changed;     /* State differs from the previous result */
	int nearest_ring; /* Ring of that edge: 0 the outer ring, 1.. the holes */
};

/* One ring. Returns 0 on success, -1 if the ring has <3 or too many vertices. */
int geofence_init(struct geofence *gf, const struct geofence_config *cfg,
		  const struct geo_point *vertices, int n, uint32_t version);

/*
 * Rings as e7 integers ([lon, lat] x 1e7), back to back, ring_len[k] each:
 * ring 0 is the outer ring, the rest are holes. Returns -1 if a ring has
 * fewer than 3 vertices or the counts are over the fence's capacity. The
 * shape rules are shape_check()'s job.
 */
int geofence_init_e7(struct geofence *gf, const struct geofence_config *cfg,
		     const int32_t (*vertices)[2], const uint16_t *ring_len, int rings,
		     uint32_t version);

/* Signed distance in metres from a point to the boundary: + inside, - outside. */
double geofence_margin_m(const struct geofence *gf, struct geo_point p);

/* Signed distance, and the ring of the nearest edge (lowest index on a tie). */
double geofence_measure(const struct geofence *gf, struct geo_point p, int *nearest_ring);

/* Feed a fix. accuracy_m is the receiver's horizontal accuracy estimate. */
struct geofence_result geofence_update(struct geofence *gf, struct geo_point p,
				       double accuracy_m);

const char *geofence_state_str(enum geofence_state s);

#endif
