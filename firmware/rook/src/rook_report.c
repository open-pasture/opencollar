/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_report.h"

#include <stdio.h>
#include <string.h>

#include "protocol.h"

const char *rook_fence_state_str(enum rook_fence_state s)
{
	switch (s) {
	case ROOK_FENCE_INSIDE:
		return "inside";
	case ROOK_FENCE_WARN:
		return "warn";
	case ROOK_FENCE_OUTSIDE:
		return "outside";
	default:
		return "none";
	}
}

struct w {
	char *b;
	size_t cap, n;
	bool err;
};

static void put(struct w *w, const char *fmt, ...) __attribute__((format(printf, 2, 3)));

#include <stdarg.h>
static void put(struct w *w, const char *fmt, ...)
{
	va_list ap;
	int k;

	if (w->err) {
		return;
	}
	va_start(ap, fmt);
	k = vsnprintf(w->b + w->n, w->cap - w->n, fmt, ap);
	va_end(ap);
	if (k < 0 || (size_t)k >= w->cap - w->n) {
		w->err = true;
		return;
	}
	w->n += (size_t)k;
}

/* e7 integer as a decimal degree with 7 places, exactly */
static void put_e7(struct w *w, int32_t v)
{
	int64_t a = v < 0 ? -(int64_t)v : v;
	char frac[8];
	int i = 7;

	snprintf(frac, sizeof(frac), "%07lld", (long long)(a % 10000000));
	while (i > 1 && frac[i - 1] == '0') {
		i--;
	}
	frac[i] = 0;
	put(w, "%s%lld.%s", v < 0 ? "-" : "", (long long)(a / 10000000), frac);
}

/* A JSON string from trusted ASCII ids (provisioning checked them); escape
 * the two characters that matter anyway */
static void put_str(struct w *w, const char *s)
{
	put(w, "\"");
	for (; s && *s; s++) {
		if (*s == '"' || *s == '\\') {
			put(w, "\\%c", *s);
		} else if ((unsigned char)*s < 0x20) {
			put(w, "\\u%04x", (unsigned char)*s);
		} else {
			put(w, "%c", *s);
		}
	}
	put(w, "\"");
}

static void put_fix(struct w *w, const struct rook_sample *s)
{
	char at[32];

	if (proto_time_format(s->at, at, sizeof(at)) < 0) {
		at[0] = 0;
	}
	put(w, "{\"at\":\"%s\",\"point\":[", at);
	put_e7(w, s->lon_e7);
	put(w, ",");
	put_e7(w, s->lat_e7);
	put(w, "],\"accuracy_m\":%u.%u,\"sats\":%u,\"fence\":\"%s\"", s->accuracy_dm / 10,
	    s->accuracy_dm % 10, s->sats, rook_fence_state_str((enum rook_fence_state)s->fence));
	if (s->fence != ROOK_FENCE_NONE) {
		int32_t m = s->margin_cm;
		uint32_t a = m < 0 ? (uint32_t)(-(int64_t)m) : (uint32_t)m;

		put(w, ",\"margin_m\":%s%u.%02u", m < 0 ? "-" : "", a / 100, a % 100);
	}
	put(w, "}");
}

int rook_report_encode(const struct rook_report_info *info, const struct rook_queue *q,
		       uint16_t max_fixes, char *out, size_t cap, uint16_t *n_fixes)
{
	struct w w = {.b = out, .cap = cap};
	char tail[160];
	struct w t = {.b = tail, .cap = sizeof(tail)};
	uint16_t n = 0;

	*n_fixes = 0;
	if (cap == 0) {
		return -1;
	}
	/* The tail first, so we know how much room the fixes have */
	put(&t, "]");
	if (info->has_battery) {
		put(&t, ",\"battery\":%.2f", (double)info->soc);
	}
	put(&t, ",\"health\":{");
	if (info->has_battery) {
		put(&t, "\"battery_v\":%.2f,", (double)info->battery_v);
	}
	if (info->has_charging) {
		put(&t, "\"charging\":%s,", info->charging ? "true" : "false");
	}
	put(&t, "\"uptime_s\":%u,\"dropped\":%u}}", (unsigned)info->uptime_s,
	    (unsigned)info->dropped);
	if (t.err) {
		return -1;
	}

	put(&w, "{\"boundary_version\":%u,\"collar_id\":", (unsigned)info->boundary_version);
	put_str(&w, info->collar_id);
	put(&w, ",\"device\":{\"fw\":");
	put_str(&w, info->fw);
	put(&w, ",\"caps\":[\"holes\",\"slots\",\"collar_id\",\"cue_mode\"]},\"fixes\":[");
	if (w.err) {
		return -1;
	}
	for (const struct rook_sample *s; n < max_fixes && (s = rook_queue_peek(q, n)); n++) {
		size_t mark = w.n;

		if (n) {
			put(&w, ",");
		}
		put_fix(&w, s);
		if (w.err || w.n + t.n >= cap) {
			w.err = false;
			w.n = mark;
			break;
		}
	}
	if (w.n + t.n >= cap) {
		return -1;
	}
	memcpy(out + w.n, tail, t.n + 1);
	*n_fixes = n;
	return (int)(w.n + t.n);
}
