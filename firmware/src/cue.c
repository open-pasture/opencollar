#include "cue.h"

#include <string.h>

/* Conservative defaults when a caller leaves welfare fields at 0.
 * REVIEW: animal-welfare expertise before shipping pulse hardware. */
#define WELFARE_DEFAULT_MAX_OUTSIDE_CUES 3
#define WELFARE_DEFAULT_ESCAPE_CYCLE_LIMIT 3
#define WELFARE_DEFAULT_ESCAPE_WINDOW_MS (24u * 60u * 60u * 1000u) /* 24 hours */

static void apply_welfare_defaults(struct cue_config *cfg)
{
	if (cfg->max_outside_cues == 0) {
		cfg->max_outside_cues = WELFARE_DEFAULT_MAX_OUTSIDE_CUES;
	}
	if (cfg->escape_cycle_limit == 0) {
		cfg->escape_cycle_limit = WELFARE_DEFAULT_ESCAPE_CYCLE_LIMIT;
	}
	if (cfg->escape_cycle_window_ms == 0) {
		cfg->escape_cycle_window_ms = WELFARE_DEFAULT_ESCAPE_WINDOW_MS;
	}
}

void cue_init(struct cue *c, const struct cue_config *cfg)
{
	memset(c, 0, sizeof(*c));
	c->cfg = *cfg;
	apply_welfare_defaults(&c->cfg);
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

static void push_welfare(struct cue *c, enum welfare_event_kind kind, int64_t now_ms)
{
	struct welfare_event ev = {
		.kind = kind,
		.at_ms = now_ms,
		.outside_cues = c->outside_cues,
		.escape_cycles = c->escape_cycles,
	};

	if (c->welfare_n == CUE_WELFARE_MAX) {
		c->welfare_head = (uint8_t)((c->welfare_head + 1) % CUE_WELFARE_MAX);
		c->welfare_n--;
	}
	c->welfare[(c->welfare_head + c->welfare_n) % CUE_WELFARE_MAX] = ev;
	c->welfare_n++;
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

bool cue_take_welfare(struct cue *c, struct welfare_event *out)
{
	if (c->welfare_n == 0) {
		return false;
	}
	*out = c->welfare[c->welfare_head];
	c->welfare_head = (uint8_t)((c->welfare_head + 1) % CUE_WELFARE_MAX);
	c->welfare_n--;
	return true;
}

bool cue_enforcement_active(const struct cue *c)
{
	return c->mode == CUE_MODE_AUDIO && !c->enforcement_off;
}

static void clear_escape_state(struct cue *c)
{
	c->escaping = false;
	c->pulse_cutoff = false;
	c->outside_cues = 0;
	c->crossed_out = false;
	c->outside_since_ms = 0;
}

static void note_return(struct cue *c, int64_t now_ms)
{
	if (!c->crossed_out) {
		clear_escape_state(c);
		return;
	}

	/* One completed escape→return cycle */
	if (c->escape_window_start_ms == 0 ||
	    now_ms - c->escape_window_start_ms >= (int64_t)c->cfg.escape_cycle_window_ms) {
		c->escape_window_start_ms = now_ms;
		c->escape_cycles = 1;
	} else {
		c->escape_cycles++;
	}

	push_welfare(c, WELFARE_RETURNED, now_ms);
	clear_escape_state(c);

	if (!c->enforcement_off && c->escape_cycles >= c->cfg.escape_cycle_limit) {
		c->enforcement_off = true;
		c->armed = false;
		push_welfare(c, WELFARE_AUTO_SHUTOFF, now_ms);
	}
}

void cue_rearm_at(struct cue *c, int64_t now_ms)
{
	/* New boundary only: arming / episode / in-progress escape state.
	 * Shut-off and escape-cycle counters stay put (Cody, Nov 3). */
	close_episode(c, EPISODE_BOUNDARY_CHANGED, now_ms);
	c->armed = false;
	c->seen_outside = false;
	c->cueing = false;
	clear_escape_state(c);
}

void cue_rearm(struct cue *c)
{
	cue_rearm_at(c, c->last_ms);
}

void cue_clear_shutoff_at(struct cue *c, int64_t now_ms)
{
	/* Caretaker only — never call from a fence / boundary update. */
	clear_escape_state(c);
	c->escape_cycles = 0;
	c->escape_window_start_ms = 0;
	if (c->enforcement_off) {
		c->enforcement_off = false;
		push_welfare(c, WELFARE_ENFORCEMENT_RESUMED, now_ms);
	}
}

void cue_clear_shutoff(struct cue *c)
{
	cue_clear_shutoff_at(c, c->last_ms);
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

static void engage_pulse_cutoff(struct cue *c, int64_t now_ms)
{
	if (c->pulse_cutoff) {
		return;
	}
	c->pulse_cutoff = true;
	c->escaping = false;
	c->cueing = false;
	push_welfare(c, WELFARE_PULSE_CUTOFF, now_ms);
}

/* The cue for this fix, and whether a forced rest began at it */
static struct cue_command decide(struct cue *c, const struct geofence_result *r, double warn_m,
				 int64_t now_ms, bool *rest_began)
{
	struct cue_command cmd = {0};
	bool want = false;
	bool outside_budget_ok;

	*rest_began = false;

	switch (r->state) {
	case GEOFENCE_INSIDE:
		if (c->crossed_out || c->escaping || c->pulse_cutoff) {
			note_return(c, now_ms);
		} else {
			clear_escape_state(c);
		}
		if (!c->enforcement_off) {
			c->armed = true;
		}
		break;
	case GEOFENCE_WARNING:
		if (!c->seen_outside && !c->enforcement_off) {
			c->armed = true;
		}
		c->escaping = false;
		break;
	case GEOFENCE_OUTSIDE:
		if (c->armed && !c->enforcement_off) {
			/* A real crossing: cue it, then stay quiet until back inside */
			c->armed = false;
			c->escaping = true;
			c->outside_since_ms = now_ms;
			c->outside_cues = 0;
			c->pulse_cutoff = false;
			/* Count toward auto shut-off only under audio enforcement */
			if (c->mode == CUE_MODE_AUDIO) {
				c->crossed_out = true;
			}
		}
		c->seen_outside = true;
		break;
	default:
		break;
	}

	if (c->mode == CUE_MODE_TRACK || c->enforcement_off) {
		return cmd;
	}

	if (r->state == GEOFENCE_WARNING && c->armed) {
		want = true;
		cmd.freq_hz = c->cfg.warn_freq_hz;
		cmd.volume = warning_volume(r->margin_m, warn_m);
		cmd.kind = CUE_WARN;
	} else if (r->state == GEOFENCE_OUTSIDE && c->escaping && !c->pulse_cutoff) {
		outside_budget_ok =
			c->outside_cues < c->cfg.max_outside_cues &&
			now_ms - c->outside_since_ms < (int64_t)c->cfg.outside_max_ms;
		if (outside_budget_ok) {
			want = true;
			cmd.freq_hz = c->cfg.outside_freq_hz;
			cmd.volume = 4;
			cmd.kind = CUE_OUTSIDE;
		} else {
			engage_pulse_cutoff(c, now_ms);
		}
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

	if (cmd.kind == CUE_OUTSIDE) {
		c->outside_cues++;
		if (c->outside_cues >= c->cfg.max_outside_cues) {
			/* Last allowed cue for this crossing; cutoff after it */
			c->escaping = false;
			if (!c->pulse_cutoff) {
				c->pulse_cutoff = true;
				/* Emit after the cue is counted, same fix */
				push_welfare(c, WELFARE_PULSE_CUTOFF, now_ms);
			}
		}
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

const char *welfare_event_str(enum welfare_event_kind k)
{
	switch (k) {
	case WELFARE_PULSE_CUTOFF:
		return "pulse_cutoff";
	case WELFARE_RETURNED:
		return "returned";
	case WELFARE_AUTO_SHUTOFF:
		return "auto_shutoff";
	case WELFARE_ENFORCEMENT_RESUMED:
		return "enforcement_resumed";
	}
	return "";
}
