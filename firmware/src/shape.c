#include "shape.h"

#include <math.h>
#include <string.h>

/*
 * Written to give the same answers as op_geo::shape bit for bit: the metric
 * part is single precision in the same order of operations, so this file
 * must be compiled without floating-point contraction (-ffp-contract=off).
 */

#define EARTH_RADIUS_M 6371008.8
#define PI_D 3.14159265358979323846
#define M_PER_DEG_LAT (EARTH_RADIUS_M * PI_D / 180.0)

void shape_init(struct shape *s, int32_t (*buf)[2], uint16_t cap)
{
	memset(s, 0, sizeof(*s));
	s->v = buf;
	s->cap = cap;
}

void shape_ring_begin(struct shape *s)
{
	if (s->rings < UINT32_MAX) {
		s->rings++;
	}
	s->cur_count = 0;
	s->cur_stored = 0;
}

void shape_vertex(struct shape *s, int64_t lon_e7, int64_t lat_e7, bool in_range)
{
	if (!in_range) {
		s->out_of_range = true;
		return;
	}
	if (s->out_of_range) {
		return; /* The code is decided; counts no longer matter */
	}

	int32_t v[2] = {(int32_t)lon_e7, (int32_t)lat_e7};

	if (s->cur_count > 0 && v[0] == s->last[0] && v[1] == s->last[1]) {
		return; /* Consecutive duplicate */
	}
	s->cur_count++;
	if (s->cur_count == 1) {
		s->first[0] = v[0];
		s->first[1] = v[1];
	}
	s->last[0] = v[0];
	s->last[1] = v[1];

	if (s->rings <= SHAPE_MAX_RINGS && s->stored < s->cap) {
		s->v[s->stored][0] = v[0];
		s->v[s->stored][1] = v[1];
		s->stored++;
		s->cur_stored++;
	} else {
		s->overflow = true;
	}
}

void shape_ring_end(struct shape *s)
{
	if (s->cur_count > 1 && s->last[0] == s->first[0] && s->last[1] == s->first[1]) {
		/* A closing vertex equal to the first */
		if (s->cur_stored == s->cur_count) {
			s->stored--;
			s->cur_stored--;
		}
		s->cur_count--;
	}
	if (s->rings >= 1 && s->rings <= SHAPE_MAX_RINGS) {
		s->len[s->rings - 1] = (uint16_t)(s->cur_count > 0xffff ? 0xffff : s->cur_count);
	}
	s->total += s->cur_count;
}

const int32_t (*shape_ring(const struct shape *s, int k))[2]
{
	uint32_t start = 0;

	for (int i = 0; i < k; i++) {
		start += s->len[i];
	}
	return (const int32_t(*)[2])&s->v[start];
}

/* ---- Exact predicates on e7 integers ---- */

typedef const int32_t (*ring_t)[2];

/* Sign of (b - a) x (c - a): 1 left turn, -1 right, 0 collinear. No overflow:
 * each product is a longitude difference (<= 3.6e9) times a latitude
 * difference (<= 1.8e9), under 2^63, and the products are compared, not subtracted. */
static int orient(const int32_t a[2], const int32_t b[2], const int32_t c[2])
{
	int64_t l = ((int64_t)b[0] - a[0]) * ((int64_t)c[1] - a[1]);
	int64_t r = ((int64_t)b[1] - a[1]) * ((int64_t)c[0] - a[0]);

	return l > r ? 1 : (l < r ? -1 : 0);
}

static int32_t min32(int32_t a, int32_t b)
{
	return a < b ? a : b;
}

static int32_t max32(int32_t a, int32_t b)
{
	return a > b ? a : b;
}

/* q inside the bounding box of p-r (for collinear points: on the segment) */
static bool on_segment(const int32_t p[2], const int32_t q[2], const int32_t r[2])
{
	return q[0] >= min32(p[0], r[0]) && q[0] <= max32(p[0], r[0]) &&
	       q[1] >= min32(p[1], r[1]) && q[1] <= max32(p[1], r[1]);
}

/* Closed segments p1p2 and q1q2 share at least one point */
static bool segments_meet(const int32_t p1[2], const int32_t p2[2], const int32_t q1[2],
			  const int32_t q2[2])
{
	int o1 = orient(p1, p2, q1);
	int o2 = orient(p1, p2, q2);
	int o3 = orient(q1, q2, p1);
	int o4 = orient(q1, q2, p2);

	if (o1 != o2 && o3 != o4) {
		return true;
	}
	return (o1 == 0 && on_segment(p1, q1, p2)) || (o2 == 0 && on_segment(p1, q2, p2)) ||
	       (o3 == 0 && on_segment(q1, p1, q2)) || (o4 == 0 && on_segment(q1, p2, q2));
}

static int sgn64(int64_t v)
{
	return (v > 0) - (v < 0);
}

/* Neighbouring edges a-b and b-c overlap beyond b: collinear, c on a's side of b */
static bool folds(const int32_t a[2], const int32_t b[2], const int32_t c[2])
{
	return orient(a, b, c) == 0 &&
	       sgn64((int64_t)c[0] - b[0]) == sgn64((int64_t)a[0] - b[0]) &&
	       sgn64((int64_t)c[1] - b[1]) == sgn64((int64_t)a[1] - b[1]);
}

/* No two edges meet except neighbours at their shared vertex */
static bool ring_simple(ring_t r, int n)
{
	for (int i = 0; i < n; i++) {
		const int32_t *a1 = r[i], *a2 = r[(i + 1) % n];

		for (int j = i + 1; j < n; j++) {
			const int32_t *b1 = r[j], *b2 = r[(j + 1) % n];

			if (j == i + 1) {
				if (folds(a1, a2, b2)) {
					return false;
				}
			} else if (i == 0 && j == n - 1) {
				if (folds(b1, b2, a2)) {
					return false;
				}
			} else if (segments_meet(a1, a2, b1, b2)) {
				return false;
			}
		}
	}
	return true;
}

static void ring_bbox(ring_t r, int n, int32_t b[4])
{
	b[0] = b[2] = r[0][0];
	b[1] = b[3] = r[0][1];
	for (int i = 1; i < n; i++) {
		b[0] = min32(b[0], r[i][0]);
		b[1] = min32(b[1], r[i][1]);
		b[2] = max32(b[2], r[i][0]);
		b[3] = max32(b[3], r[i][1]);
	}
}

static bool boxes_meet(const int32_t a[4], const int32_t b[4])
{
	return a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
}

static bool rings_meet(ring_t a, int n, ring_t b, int m)
{
	for (int i = 0; i < n; i++) {
		for (int j = 0; j < m; j++) {
			if (segments_meet(a[i], a[(i + 1) % n], b[j], b[(j + 1) % m])) {
				return true;
			}
		}
	}
	return false;
}

/* Even-odd rule toward +x. p must not lie on the ring. */
static bool inside(const int32_t p[2], ring_t r, int n)
{
	bool c = false;

	for (int i = 0, j = n - 1; i < n; j = i++) {
		const int32_t *a = r[i], *b = r[j];

		if ((a[1] > p[1]) != (b[1] > p[1])) {
			/* The crossing is right of p: p.x < a.x + (p.y - a.y)(b.x - a.x)/(b.y - a.y) */
			int64_t lhs = ((int64_t)p[0] - a[0]) * ((int64_t)b[1] - a[1]);
			int64_t rhs = ((int64_t)p[1] - a[1]) * ((int64_t)b[0] - a[0]);

			if (b[1] > a[1] ? lhs < rhs : lhs > rhs) {
				c = !c;
			}
		}
	}
	return c;
}

/* ---- Single-precision areas and distances ---- */

struct metric {
	int64_t lon0, lat0;
	float kx, ky;
};

static void metric_init(struct metric *m, const int32_t origin[2])
{
	double lat0_deg = (double)origin[1] / 1e7;
	double m_per_deg_lon = M_PER_DEG_LAT * cos(lat0_deg * (PI_D / 180.0));

	m->lon0 = origin[0];
	m->lat0 = origin[1];
	m->kx = (float)(m_per_deg_lon * 1e-7);
	m->ky = (float)(M_PER_DEG_LAT * 1e-7);
}

static void xy(const struct metric *m, const int32_t p[2], float out[2])
{
	out[0] = (float)((int64_t)p[0] - m->lon0) * m->kx;
	out[1] = (float)((int64_t)p[1] - m->lat0) * m->ky;
}

/* Fan sum from the first vertex, in index order */
static float ring_area(const struct metric *m, ring_t r, int n)
{
	float o[2], a[2], b[2];
	float s = 0.0f;

	xy(m, r[0], o);
	for (int i = 1; i < n - 1; i++) {
		xy(m, r[i], a);
		xy(m, r[i + 1], b);

		float ax = a[0] - o[0], ay = a[1] - o[1];
		float bx = b[0] - o[0], by = b[1] - o[1];

		s += ax * by - ay * bx;
	}
	return fabsf(s * 0.5f);
}

static float segment_distance(const float p[2], const float a[2], const float b[2])
{
	float dx = b[0] - a[0], dy = b[1] - a[1];
	float len2 = dx * dx + dy * dy;
	float t = 0.0f;

	if (len2 > 0.0f) {
		t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2;
		if (t < 0.0f) {
			t = 0.0f;
		} else if (t > 1.0f) {
			t = 1.0f;
		}
	}

	float cx = a[0] + t * dx - p[0];
	float cy = a[1] + t * dy - p[1];

	return sqrtf(cx * cx + cy * cy);
}

static float point_ring(const struct metric *m, const float p[2], ring_t r, int n)
{
	float best = INFINITY;
	float a[2], b[2];

	for (int i = 0; i < n; i++) {
		xy(m, r[i], a);
		xy(m, r[(i + 1) % n], b);

		float d = segment_distance(p, a, b);

		if (d < best) {
			best = d;
		}
	}
	return best;
}

/* Least distance between two rings that don't meet */
static float ring_distance(const struct metric *m, ring_t a, int n, ring_t b, int k)
{
	float ab = INFINITY, ba = INFINITY;
	float p[2];

	for (int i = 0; i < n; i++) {
		xy(m, a[i], p);

		float d = point_ring(m, p, b, k);

		if (d < ab) {
			ab = d;
		}
	}
	for (int i = 0; i < k; i++) {
		xy(m, b[i], p);

		float d = point_ring(m, p, a, n);

		if (d < ba) {
			ba = d;
		}
	}
	return ab < ba ? ab : ba;
}

static void metric_bbox(const struct metric *m, ring_t r, int n, float b[4])
{
	float p[2];

	b[0] = b[1] = INFINITY;
	b[2] = b[3] = -INFINITY;
	for (int i = 0; i < n; i++) {
		xy(m, r[i], p);
		b[0] = fminf(b[0], p[0]);
		b[1] = fminf(b[1], p[1]);
		b[2] = fmaxf(b[2], p[0]);
		b[3] = fmaxf(b[3], p[1]);
	}
}

static float box_distance(const float a[4], const float b[4])
{
	float dx = fmaxf(fmaxf(b[0] - a[2], a[0] - b[2]), 0.0f);
	float dy = fmaxf(fmaxf(b[1] - a[3], a[1] - b[3]), 0.0f);

	return sqrtf(dx * dx + dy * dy);
}

static bool margin_ok(double v)
{
	return isfinite(v) && v >= 0.0 && v <= SHAPE_MAX_MARGIN_M;
}

enum reject_code shape_check(const struct shape *s, const struct collar_limits *limits,
			     double warn_m, double hysteresis_m, double slack_m)
{
	if (!margin_ok(warn_m) || !margin_ok(hysteresis_m)) {
		return REJECT_BAD_MARGINS;
	}
	if (shape_holes(s) > limits->holes) {
		return REJECT_TOO_MANY_HOLES;
	}
	if (s->out_of_range) {
		return REJECT_OUT_OF_RANGE;
	}
	if (s->rings == 0 || s->rings > SHAPE_MAX_RINGS) {
		/* No outer ring at all; more rings than any limit is caught above */
		return s->rings == 0 ? REJECT_TOO_FEW_VERTICES : REJECT_TOO_MANY_HOLES;
	}

	int n = (int)s->rings;

	for (int k = 0; k < n; k++) {
		if (s->len[k] < 3) {
			return REJECT_TOO_FEW_VERTICES;
		}
	}
	if (s->len[0] > limits->outer || s->total > limits->total) {
		return REJECT_TOO_MANY_VERTICES;
	}
	for (int k = 1; k < n; k++) {
		if (s->len[k] > limits->hole_vertices) {
			return REJECT_TOO_MANY_VERTICES;
		}
	}
	if (s->overflow) {
		return REJECT_TOO_MANY_VERTICES; /* Unreachable within any limit */
	}

	ring_t r[SHAPE_MAX_RINGS];
	int32_t box[SHAPE_MAX_RINGS][4];

	for (int k = 0, start = 0; k < n; start += s->len[k], k++) {
		r[k] = (ring_t)&s->v[start];
	}
	for (int k = 0; k < n; k++) {
		if (!ring_simple(r[k], s->len[k])) {
			return REJECT_SELF_INTERSECTING;
		}
	}
	for (int k = 0; k < n; k++) {
		ring_bbox(r[k], s->len[k], box[k]);
	}
	for (int i = 0; i < n; i++) {
		for (int j = i + 1; j < n; j++) {
			if (boxes_meet(box[i], box[j]) &&
			    rings_meet(r[i], s->len[i], r[j], s->len[j])) {
				return REJECT_RINGS_CROSS;
			}
		}
	}
	for (int k = 1; k < n; k++) {
		if (!inside(r[k][0], r[0], s->len[0])) {
			return REJECT_HOLE_OUTSIDE;
		}
	}
	for (int i = 1; i < n; i++) {
		for (int j = i + 1; j < n; j++) {
			if (inside(r[j][0], r[i], s->len[i]) || inside(r[i][0], r[j], s->len[j])) {
				return REJECT_HOLES_OVERLAP;
			}
		}
	}

	struct metric m;

	metric_init(&m, r[0][0]);
	if (ring_area(&m, r[0], s->len[0]) < 1.0f) {
		return REJECT_ZERO_AREA;
	}
	for (int k = 1; k < n; k++) {
		if (ring_area(&m, r[k], s->len[k]) < 100.0f) {
			return REJECT_HOLE_TOO_SMALL;
		}
	}

	double gap = shape_min_gap_m(warn_m) + slack_m;
	float fbox[SHAPE_MAX_RINGS][4];

	for (int k = 0; k < n; k++) {
		metric_bbox(&m, r[k], s->len[k], fbox[k]);
	}
	for (int i = 0; i < n; i++) {
		for (int j = i + 1; j < n; j++) {
			if ((double)box_distance(fbox[i], fbox[j]) < gap &&
			    (double)ring_distance(&m, r[i], s->len[i], r[j], s->len[j]) < gap) {
				return REJECT_HOLE_TOO_CLOSE;
			}
		}
	}
	return REJECT_NONE;
}
