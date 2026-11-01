/*
 * Cue policy: turns geofence results into audio cues. Plain C, host-testable.
 *
 * V0 is audio only. Warning-zone cues get louder the closer the animal is to
 * the edge. Once outside, a distinct tone plays for a limited time and then
 * stops, so an animal that has escaped isn't cued indefinitely. Continuous
 * cueing is capped and followed by a rest period, which also stops GPS drift
 * near the edge from causing endless beeping.
 *
 * Only a crossing is cued. The fence is armed by an inside fix and disarmed by
 * boot, a new boundary (cue_rearm) or a crossing. While unarmed the collar is
 * silent: an animal a new boundary leaves outside isn't cued, and neither is
 * one walking back in through the warning zone. An audio cue only teaches
 * when the animal can escape it by moving away from the edge.
 *
 * What arms it: after boot or a new boundary, the first fix inside the polygon
 * (inside or warning), so an animal a new boundary puts in the warning zone is
 * cued straight away. Once the collar has seen the animal outside, only a fix
 * clear of the warning zone arms it again. Walking into a hole is a crossing
 * like any other; a hole drawn on top of an animal leaves it outside and
 * silent until it has walked clear of the warning zone.
 *
 * Protocol v1 (§3.6) adds cue kinds (warn, outside), a track mode that
 * evaluates the fence without sound, and episodes: a run of armed warning
 * cues, ending turned_back (the animal reached inside), crossed, rest (the
 * 20 s cap forced a rest) or boundary_changed (a new boundary or mode).
 *
 * Welfare (see docs/WELFARE-POLICY.md): outside cues are count-capped per
 * crossing (pulse cutoff), then suspended until the animal is clear inside;
 * repeated escape→return cycles auto-shut off enforcement for that animal.
 * Thresholds are conservative defaults and need animal-welfare review.
 * Welfare events are queued like episodes so they stay observable.
 */
#ifndef OPENCOLLAR_CUE_H
#define OPENCOLLAR_CUE_H

#include <stdbool.h>
#include <stdint.h>

#include "geofence.h"

struct cue_config {
	uint16_t warn_freq_hz;
	uint16_t outside_freq_hz;
	uint16_t beep_ms;        /* Length of each beep; one beep per fix */
	uint32_t max_active_ms;  /* Longest continuous cue before a forced rest */
	uint32_t rest_ms;        /* Silence after hitting max_active_ms */
	uint32_t outside_max_ms; /* How long to cue after leaving the polygon */

	/*
	 * Welfare thresholds. REVIEW: pick final values with animal-welfare
	 * expertise. Zero at cue_init() is replaced by the safe defaults
	 * (2 outside cues, 3 cycles / hour). Use 255 / UINT32_MAX only in
	 * tests that deliberately disable a limit.
	 */
	uint8_t max_outside_cues;        /* Outside/pulse cues per crossing; default 2 */
	uint8_t escape_cycle_limit;      /* Escape→return cycles before shut-off; default 3 */
	uint32_t escape_cycle_window_ms; /* Rolling window for those cycles; default 1 h */
};

enum cue_kind {
	CUE_NONE = 0,
	CUE_WARN,    /* The warning tone, louder toward the edge */
	CUE_OUTSIDE, /* The tone after a crossing, for up to 10 s / cue budget */
};

enum cue_mode {
	CUE_MODE_AUDIO = 0, /* Cue the animal */
	CUE_MODE_TRACK,     /* Evaluate the fence and report state only */
};

struct cue_command {
	bool active;
	uint16_t freq_hz;
	uint8_t volume; /* 0-4, matches the Qwiic Buzzer */
	uint16_t duration_ms;
	enum cue_kind kind; /* Set whenever active */
};

enum episode_outcome {
	EPISODE_TURNED_BACK = 0,
	EPISODE_CROSSED,
	EPISODE_REST,
	EPISODE_BOUNDARY_CHANGED,
};

/* A run of armed warning cues. Times are ms on the caller's clock (cue_update's now_ms). */
struct episode {
	int64_t start;       /* The first warning cue */
	int64_t end;         /* The fix (or boundary change) that ended it */
	int ring;            /* Nearest ring at the first cue: 0 outer, 1.. holes */
	uint32_t cues;       /* Warning cues played */
	uint8_t max_level;   /* Loudest warning cue */
	double min_margin_m; /* Least margin over its fixes, the ending one included */
	enum episode_outcome outcome;
};

/* Ended episodes kept until taken; the oldest is dropped beyond this */
#define CUE_EPISODES_MAX 8

enum welfare_event_kind {
	WELFARE_PULSE_CUTOFF = 0,    /* Outside cue budget spent; suspended until inside */
	WELFARE_RETURNED,            /* Clear inside after a crossing (one escape cycle) */
	WELFARE_AUTO_SHUTOFF,        /* Escape-cycle limit hit; enforcement off */
	WELFARE_ENFORCEMENT_RESUMED, /* Cleared by a new boundary / rearm */
};

struct welfare_event {
	enum welfare_event_kind kind;
	int64_t at_ms;
	uint8_t outside_cues;  /* Outside cues delivered on the crossing just ended */
	uint8_t escape_cycles; /* Cycles counted in the window at this event */
};

#define CUE_WELFARE_MAX 8

struct cue {
	struct cue_config cfg;
	enum cue_mode mode;
	bool cueing;
	int64_t active_since_ms;
	int64_t rest_until_ms;
	int64_t outside_since_ms;
	bool armed;        /* An inside fix under the current boundary; cues allowed */
	bool seen_outside; /* Outside since the last rearm, so warning doesn't arm */
	bool escaping;     /* Crossed out; the outside tone window is running */
	int64_t last_ms;   /* Time of the last fix */

	/* Welfare state */
	uint8_t outside_cues;           /* Outside cues delivered this escape */
	bool pulse_cutoff;              /* Budget spent; silent until clear inside */
	bool crossed_out;               /* A real crossing is open until returned */
	uint8_t escape_cycles;          /* Completed escape→return cycles in the window */
	int64_t escape_window_start_ms; /* Start of the current cycle window; 0 = none */
	bool enforcement_off;           /* Auto shut-off: no cues until rearm */

	bool ep_open;
	struct episode ep;
	struct episode done[CUE_EPISODES_MAX];
	uint8_t done_head, done_n;

	struct welfare_event welfare[CUE_WELFARE_MAX];
	uint8_t welfare_head, welfare_n;
};

/* Starts unarmed, in audio mode. Missing welfare fields (zero) get safe defaults. */
void cue_init(struct cue *c, const struct cue_config *cfg);

/* Call whenever a new boundary is applied: silent until the next inside fix.
 * Keeps any forced rest that is running. A running episode ends as
 * boundary_changed at the last fix's time. Clears auto shut-off. */
void cue_rearm(struct cue *c);

/* cue_rearm() at now_ms */
void cue_rearm_at(struct cue *c, int64_t now_ms);

/* Switch between cueing and tracking only. A running episode ends as
 * boundary_changed: the mode comes with a boundary. */
void cue_set_mode(struct cue *c, enum cue_mode mode);

struct cue_command cue_update(struct cue *c, const struct geofence_result *r,
			      double warn_m, int64_t now_ms);

/* Oldest ended episode not yet taken. */
bool cue_take_episode(struct cue *c, struct episode *out);

/* Oldest welfare event not yet taken. */
bool cue_take_welfare(struct cue *c, struct welfare_event *out);

/* True when audio/pulse enforcement is allowed (not auto-shut-off, not track). */
bool cue_enforcement_active(const struct cue *c);

const char *cue_kind_str(enum cue_kind k);
const char *episode_outcome_str(enum episode_outcome o);
const char *welfare_event_str(enum welfare_event_kind k);

#endif
