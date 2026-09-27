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
};

enum cue_kind {
	CUE_NONE = 0,
	CUE_WARN,    /* The warning tone, louder toward the edge */
	CUE_OUTSIDE, /* The tone after a crossing, for up to 10 s */
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

	bool ep_open;
	struct episode ep;
	struct episode done[CUE_EPISODES_MAX];
	uint8_t done_head, done_n;
};

/* Starts unarmed, in audio mode. */
void cue_init(struct cue *c, const struct cue_config *cfg);

/* Call whenever a new boundary is applied: silent until the next inside fix.
 * Keeps any forced rest that is running. A running episode ends as
 * boundary_changed at the last fix's time. */
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

const char *cue_kind_str(enum cue_kind k);
const char *episode_outcome_str(enum episode_outcome o);

#endif
