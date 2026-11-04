#include "report.h"

#include <stdio.h>
#include <string.h>

#include "protocol.h"

const char *const REPORT_CAPS[] = {
	"holes", "slots", "collar_id", "cue_mode", "episodes", "config", OC_CAP_REARM,
};
const size_t REPORT_CAPS_N = sizeof(REPORT_CAPS) / sizeof(REPORT_CAPS[0]);

/* RAM-only telemetry; cleared on reboot. Not NVS. */
static bool g_has_last_cue_at;
static int64_t g_last_cue_at;
static bool g_has_rsrp;
static int g_rsrp_dbm;

void report_note_cue_at(int64_t utc_s)
{
	g_has_last_cue_at = true;
	g_last_cue_at = utc_s;
}

void report_clear_last_cue_at(void)
{
	g_has_last_cue_at = false;
	g_last_cue_at = 0;
}

bool report_get_last_cue_at(int64_t *out)
{
	if (!g_has_last_cue_at) {
		return false;
	}
	if (out) {
		*out = g_last_cue_at;
	}
	return true;
}

void report_set_signal_dbm(int rsrp_dbm)
{
	g_has_rsrp = true;
	g_rsrp_dbm = rsrp_dbm;
}

void report_clear_signal_dbm(void)
{
	g_has_rsrp = false;
	g_rsrp_dbm = 0;
}

bool report_get_signal_dbm(int *out)
{
	if (!g_has_rsrp) {
		return false;
	}
	if (out) {
		*out = g_rsrp_dbm;
	}
	return true;
}

int report_encode_welfare(const struct report_welfare *w, char *out, size_t cap)
{
	char shut[24];
	int n;

	if (w->enforcement_off && w->has_shutoff_at) {
		if (proto_time_format(w->shutoff_at, shut, sizeof(shut)) <= 0) {
			return -1;
		}
		n = snprintf(out, cap,
			     "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":%u,\"%s\":%u}", OC_FIELD_ENFORCEMENT,
			     OC_ENFORCEMENT_OFF, OC_FIELD_SHUTOFF_AT, shut, OC_FIELD_ESCAPE_CYCLES,
			     (unsigned)w->escape_cycles, OC_FIELD_REARM_SEQ, (unsigned)w->rearm_seq);
	} else {
		n = snprintf(out, cap, "{\"%s\":\"%s\",\"%s\":%u,\"%s\":%u}", OC_FIELD_ENFORCEMENT,
			     w->enforcement_off ? OC_ENFORCEMENT_OFF : OC_ENFORCEMENT_ON,
			     OC_FIELD_ESCAPE_CYCLES, (unsigned)w->escape_cycles, OC_FIELD_REARM_SEQ,
			     (unsigned)w->rearm_seq);
	}
	if (n < 0 || (size_t)n >= cap) {
		return -1;
	}
	return n;
}

int report_encode_welfare_event(const struct welfare_event *e, bool has_at_utc, int64_t at_utc,
				char *out, size_t cap)
{
	const char *kind = welfare_event_str(e->kind);
	char at[24];
	int n;

	if (!kind || !kind[0]) {
		return -1;
	}
	if (has_at_utc) {
		if (proto_time_format(at_utc, at, sizeof(at)) <= 0) {
			return -1;
		}
	} else {
		at[0] = '\0';
	}

	if (e->kind == WELFARE_ENFORCEMENT_RESUMED && e->has_by) {
		if (has_at_utc) {
			n = snprintf(out, cap,
				     "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":%u,"
				     "\"%s\":%u,\"%s\":%u}",
				     OC_FIELD_KIND, kind, OC_FIELD_AT, at, OC_FIELD_BY, e->by,
				     OC_FIELD_OUTSIDE_CUES, (unsigned)e->outside_cues,
				     OC_FIELD_ESCAPE_CYCLES, (unsigned)e->escape_cycles,
				     OC_FIELD_REARM_SEQ, (unsigned)e->rearm_seq);
		} else {
			n = snprintf(out, cap,
				     "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":%u,\"%s\":%u,\"%s\":%u}",
				     OC_FIELD_KIND, kind, OC_FIELD_BY, e->by, OC_FIELD_OUTSIDE_CUES,
				     (unsigned)e->outside_cues, OC_FIELD_ESCAPE_CYCLES,
				     (unsigned)e->escape_cycles, OC_FIELD_REARM_SEQ,
				     (unsigned)e->rearm_seq);
		}
	} else if (has_at_utc) {
		n = snprintf(out, cap, "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":%u,\"%s\":%u}",
			     OC_FIELD_KIND, kind, OC_FIELD_AT, at, OC_FIELD_OUTSIDE_CUES,
			     (unsigned)e->outside_cues, OC_FIELD_ESCAPE_CYCLES,
			     (unsigned)e->escape_cycles);
	} else {
		n = snprintf(out, cap, "{\"%s\":\"%s\",\"%s\":%u,\"%s\":%u}", OC_FIELD_KIND, kind,
			     OC_FIELD_OUTSIDE_CUES, (unsigned)e->outside_cues, OC_FIELD_ESCAPE_CYCLES,
			     (unsigned)e->escape_cycles);
	}
	if (n < 0 || (size_t)n >= cap) {
		return -1;
	}
	return n;
}

/* Degrees with at most 7 decimals; trim trailing zeros (protocol style). */
static int put_deg(char *out, size_t cap, double deg)
{
	int n = snprintf(out, cap, "%.7f", deg);
	char *dot;

	if (n < 0 || (size_t)n >= cap) {
		return n;
	}
	dot = strchr(out, '.');
	if (!dot) {
		return n;
	}
	while (n > 0 && out[n - 1] == '0') {
		out[--n] = '\0';
	}
	if (n > 0 && out[n - 1] == '.') {
		out[--n] = '\0';
	}
	return n;
}

int report_encode_fix(const struct report_fix *f, char *out, size_t cap)
{
	char at[24];
	char lon[32], lat[32];
	int n, k;
	size_t used = 0;

	if (proto_time_format(f->at, at, sizeof(at)) <= 0) {
		return -1;
	}
	if (put_deg(lon, sizeof(lon), f->lon) < 0 || put_deg(lat, sizeof(lat), f->lat) < 0) {
		return -1;
	}

	n = snprintf(out, cap, "{\"%s\":\"%s\",\"%s\":[%s,%s],\"%s\":%.1f", OC_FIELD_AT, at,
		     OC_FIELD_POINT, lon, lat, OC_FIELD_ACCURACY_M, f->accuracy_m);
	if (n < 0 || (size_t)n >= cap) {
		return -1;
	}
	used = (size_t)n;

	if (f->has_sats) {
		k = snprintf(out + used, cap - used, ",\"%s\":%u", OC_FIELD_SATS, (unsigned)f->sats);
		if (k < 0 || (size_t)k >= cap - used) {
			return -1;
		}
		used += (size_t)k;
	}
	if (f->has_cn0) {
		k = snprintf(out + used, cap - used, ",\"%s\":%.1f", OC_FIELD_CN0, f->cn0);
		if (k < 0 || (size_t)k >= cap - used) {
			return -1;
		}
		used += (size_t)k;
	}
	if (f->has_hdop) {
		k = snprintf(out + used, cap - used, ",\"%s\":%.1f", OC_FIELD_HDOP, f->hdop);
		if (k < 0 || (size_t)k >= cap - used) {
			return -1;
		}
		used += (size_t)k;
	}

	if (used + 1 >= cap) {
		return -1;
	}
	out[used++] = '}';
	out[used] = '\0';
	return (int)used;
}

int report_encode_battery(bool known, double soc, char *out, size_t cap)
{
	int n;

	if (!known) {
		if (cap > 0) {
			out[0] = '\0';
		}
		return 0;
	}
	n = snprintf(out, cap, "\"%s\":%.2f", OC_FIELD_BATTERY, soc);
	if (n < 0 || (size_t)n >= cap) {
		return -1;
	}
	return n;
}

int report_encode_health_telemetry(char *out, size_t cap)
{
	char at[24];
	int n;
	size_t used = 0;
	bool any = false;

	if (cap < 3) {
		return -1;
	}
	out[used++] = '{';
	out[used] = '\0';

	if (g_has_last_cue_at) {
		if (proto_time_format(g_last_cue_at, at, sizeof(at)) <= 0) {
			return -1;
		}
		n = snprintf(out + used, cap - used, "\"%s\":\"%s\"", OC_FIELD_LAST_CUE_AT, at);
		if (n < 0 || (size_t)n >= cap - used) {
			return -1;
		}
		used += (size_t)n;
		any = true;
	}
	if (g_has_rsrp) {
		n = snprintf(out + used, cap - used, "%s\"%s\":%d", any ? "," : "", OC_FIELD_RSRP_DBM,
			     g_rsrp_dbm);
		if (n < 0 || (size_t)n >= cap - used) {
			return -1;
		}
		used += (size_t)n;
		any = true;
	}
	(void)any;

	if (used + 1 >= cap) {
		return -1;
	}
	out[used++] = '}';
	out[used] = '\0';
	return (int)used;
}
