/*
 * Cue policy: turns geofence results into audio cues. Plain C, host-testable.
 *
 * V0 is audio only. Warning-zone cues get louder the closer the animal is to
 * the edge. Once outside, a distinct tone plays for a limited time and then
 * stops, so an animal that has escaped isn't cued indefinitely. Continuous
 * cueing is capped and followed by a rest period, which also stops GPS drift
 * near the edge from causing endless beeping.
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
	enum geofence_state last_state;
};

void cue_init(struct cue *c, const struct cue_config *cfg);

struct cue_command cue_update(struct cue *c, const struct geofence_result *r,
			      double warn_m, int64_t now_ms);

#endif
