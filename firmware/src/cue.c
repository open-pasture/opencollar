#include "cue.h"

#include <string.h>

void cue_init(struct cue *c, const struct cue_config *cfg)
{
	memset(c, 0, sizeof(*c));
	c->cfg = *cfg;
	c->last_state = GEOFENCE_UNKNOWN;
}

static uint8_t warning_volume(double margin_m, double warn_m)
{
	/* 1 at the inner edge of the zone, 4 at the boundary */
	double depth = warn_m - margin_m;
	int v = 1 + (int)(3.0 * depth / warn_m);

	if (v < 1) {
		v = 1;
	} else if (v > 4) {
		v = 4;
	}
	return (uint8_t)v;
}

struct cue_command cue_update(struct cue *c, const struct geofence_result *r,
			      double warn_m, int64_t now_ms)
{
	struct cue_command cmd = {0};
	bool want = false;

	if (r->state == GEOFENCE_OUTSIDE && c->last_state != GEOFENCE_OUTSIDE) {
		c->outside_since_ms = now_ms;
	}
	c->last_state = r->state;

	if (r->state == GEOFENCE_WARNING) {
		want = true;
		cmd.freq_hz = c->cfg.warn_freq_hz;
		cmd.volume = warning_volume(r->margin_m, warn_m);
	} else if (r->state == GEOFENCE_OUTSIDE &&
		   now_ms - c->outside_since_ms < (int64_t)c->cfg.outside_max_ms) {
		want = true;
		cmd.freq_hz = c->cfg.outside_freq_hz;
		cmd.volume = 4;
	}

	if (!want) {
		c->cueing = false;
		return (struct cue_command){0};
	}

	if (now_ms < c->rest_until_ms) {
		return (struct cue_command){0};
	}

	if (!c->cueing) {
		c->cueing = true;
		c->active_since_ms = now_ms;
	} else if (now_ms - c->active_since_ms >= (int64_t)c->cfg.max_active_ms) {
		c->cueing = false;
		c->rest_until_ms = now_ms + c->cfg.rest_ms;
		return (struct cue_command){0};
	}

	cmd.active = true;
	cmd.duration_ms = c->cfg.beep_ms;
	return cmd;
}
