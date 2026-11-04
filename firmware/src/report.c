#include "report.h"

#include <stdio.h>
#include <string.h>

#include "protocol.h"

const char *const REPORT_CAPS[] = {
	"holes", "slots", "collar_id", "cue_mode", "episodes", "config", OC_CAP_REARM,
};
const size_t REPORT_CAPS_N = sizeof(REPORT_CAPS) / sizeof(REPORT_CAPS[0]);

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
