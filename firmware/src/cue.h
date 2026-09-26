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
 * clear of the warning zone arms it again.
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

struct cue_command {
	bool active;
	uint16_t freq_hz;
	uint8_t volume; /* 0-4, matches the Qwiic Buzzer */
	uint16_t duration_ms;
};

struct cue {
	struct cue_config cfg;
	bool cueing;
	int64_t active_since_ms;
	int64_t rest_until_ms;
	int64_t outside_since_ms;
	bool armed;        /* An inside fix under the current boundary; cues allowed */
	bool seen_outside; /* Outside since the last rearm, so warning doesn't arm */
	bool escaping;     /* Crossed out; the outside tone window is running */
};

/* Starts unarmed. */
void cue_init(struct cue *c, const struct cue_config *cfg);

/* Call whenever a new boundary is applied: silent until the next inside fix.
 * Keeps any forced rest that is running. */
void cue_rearm(struct cue *c);

struct cue_command cue_update(struct cue *c, const struct geofence_result *r,
			      double warn_m, int64_t now_ms);

#endif
