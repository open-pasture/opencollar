#include "cue.h"

#include <string.h>

void cue_init(struct cue *c, const struct cue_config *cfg)
{
	memset(c, 0, sizeof(*c));
	c->cfg = *cfg;
}

static void push_done(struct cue *c, const struct episode *ep)
{
	if (c->done_n == CUE_EPISODES_MAX) {
		c->done_head = (uint8_t)((c->done_head + 1) % CUE_EPISODES_MAX);
		c->done_n--;
	}
	c->done[(c->done_head + c->done_n) % CUE_EPISODES_MAX] = *ep;
	c->done_n++;
}

static void close_episode(struct cue *c, enum episode_outcome outcome, int64_t now_ms)
{
	if (!c->ep_open) {
		return;
	}
	c->ep.end = now_ms;
	c->ep.outcome = outcome;
	c->ep_open = false;
	push_done(c, &c->ep);
}

bool cue_take_episode(struct cue *c, struct episode *out)
{
	if (c->done_n == 0) {
		return false;
	}
	*out = c->done[c->done_head];
	c->done_head = (uint8_t)((c->done_head + 1) % CUE_EPISODES_MAX);
	c->done_n--;
	return true;
}

void cue_rearm_at(struct cue *c, int64_t now_ms)
{
	close_episode(c, EPISODE_BOUNDARY_CHANGED, now_ms);
	c->armed = false;
	c->seen_outside = false;
	c->escaping = false;
	c->cueing = false;
}

void cue_rearm(struct cue *c)
{
	cue_rearm_at(c, c->last_ms);
}

void cue_set_mode(struct cue *c, enum cue_mode mode)
{
	if (mode != c->mode) {
		close_episode(c, EPISODE_BOUNDARY_CHANGED, c->last_ms);
		c->cueing = false;
	}
	c->mode = mode;
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

/* The cue for this fix, and whether a forced rest began at it */
static struct cue_command decide(struct cue *c, const struct geofence_result *r, double warn_m,
				 int64_t now_ms, bool *rest_began)
{
	struct cue_command cmd = {0};
	bool want = false;

	*rest_began = false;

	switch (r->state) {
	case GEOFENCE_INSIDE:
		c->armed = true;
		c->escaping = false;
		break;
	case GEOFENCE_WARNING:
		if (!c->seen_outside) {
			c->armed = true;
		}
		c->escaping = false;
		break;
	case GEOFENCE_OUTSIDE:
		if (c->armed) {
			/* A real crossing: cue it, then stay quiet until back inside */
			c->armed = false;
			c->escaping = true;
			c->outside_since_ms = now_ms;
		}
		c->seen_outside = true;
		break;
	default:
		break;
	}

	if (c->mode == CUE_MODE_TRACK) {
		return cmd;
	}

	if (r->state == GEOFENCE_WARNING && c->armed) {
		want = true;
		cmd.freq_hz = c->cfg.warn_freq_hz;
		cmd.volume = warning_volume(r->margin_m, warn_m);
		cmd.kind = CUE_WARN;
	} else if (r->state == GEOFENCE_OUTSIDE && c->escaping &&
		   now_ms - c->outside_since_ms < (int64_t)c->cfg.outside_max_ms) {
		want = true;
		cmd.freq_hz = c->cfg.outside_freq_hz;
		cmd.volume = 4;
		cmd.kind = CUE_OUTSIDE;
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
		*rest_began = true;
		return (struct cue_command){0};
	}

	cmd.active = true;
	cmd.duration_ms = c->cfg.beep_ms;
	return cmd;
}

/* Episode bookkeeping after each fix */
static void observe(struct cue *c, const struct geofence_result *r, const struct cue_command *cmd,
		    bool rest_began, int64_t now_ms)
{
	bool warn = cmd->active && cmd->kind == CUE_WARN;

	if (c->ep_open) {
		if (r->margin_m < c->ep.min_margin_m) {
			c->ep.min_margin_m = r->margin_m;
		}
		if (warn) {
			c->ep.cues++;
			if (cmd->volume > c->ep.max_level) {
				c->ep.max_level = cmd->volume;
			}
		}
		if (r->state == GEOFENCE_OUTSIDE) {
			close_episode(c, EPISODE_CROSSED, now_ms);
		} else if (r->state == GEOFENCE_INSIDE) {
			close_episode(c, EPISODE_TURNED_BACK, now_ms);
		} else if (rest_began) {
			close_episode(c, EPISODE_REST, now_ms);
		}
		return;
	}
	if (warn) {
		c->ep_open = true;
		c->ep = (struct episode){
			.start = now_ms,
			.end = now_ms,
			.ring = r->nearest_ring,
			.cues = 1,
			.max_level = cmd->volume,
			.min_margin_m = r->margin_m,
			.outcome = EPISODE_TURNED_BACK,
		};
	}
}

struct cue_command cue_update(struct cue *c, const struct geofence_result *r,
			      double warn_m, int64_t now_ms)
{
	bool rest_began;
	struct cue_command cmd;

	c->last_ms = now_ms;
	cmd = decide(c, r, warn_m, now_ms, &rest_began);
	if (c->mode == CUE_MODE_TRACK) {
		return (struct cue_command){0};
	}
	observe(c, r, &cmd, rest_began, now_ms);
	return cmd;
}

const char *cue_kind_str(enum cue_kind k)
{
	switch (k) {
	case CUE_WARN:
		return "warn";
	case CUE_OUTSIDE:
		return "outside";
	default:
		return "";
	}
}

const char *episode_outcome_str(enum episode_outcome o)
{
	switch (o) {
	case EPISODE_TURNED_BACK:
		return "turned_back";
	case EPISODE_CROSSED:
		return "crossed";
	case EPISODE_REST:
		return "rest";
	case EPISODE_BOUNDARY_CHANGED:
		return "boundary_changed";
	}
	return "";
}
