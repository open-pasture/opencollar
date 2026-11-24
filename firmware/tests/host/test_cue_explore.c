/*
 * Every sequence of collar events up to DEPTH steps, run through the real cue.c,
 * checked against the welfare shut-off rules after each step. This is the code-level
 * half of firmware/formal/Shutoff.tla: the model checks the design, this checks that
 * cue.c keeps the same rules (.claude/skills/verify-shutoff-and-gossip/SKILL.md).
 *
 * Rules, as cue.h states them:
 *   R1  No cue sounds while auto shut-off is on.
 *   R2  Only the caretaker re-arm (cue_clear_shutoff) turns shut-off off. A new
 *       boundary (cue_rearm, #22) or a mode change never does.
 *   R3  At most max_outside_cues outside cues per crossing (pulse cutoff).
 *
 * Reboot is not explored: on main the cue state is RAM and a reboot clears shut-off
 * (finding F1 in the skill; #25 persists it).
 */
#include "test.h"

#include "../../src/cue.h"

#define DEPTH 9

enum ev { EV_INSIDE, EV_WARNING, EV_OUTSIDE, EV_BOUNDARY, EV_CARETAKER, EV_DAY, EV_MODE, EV_N };

static const char *const EV_NAME[EV_N] = {
	"fix inside", "fix in warning zone", "fix outside", "new boundary (cue_rearm)",
	"caretaker re-arm (cue_clear_shutoff)", "25 h pass, then fix inside", "toggle audio/track",
};

static const struct cue_config CFG = {
	.warn_freq_hz = 2730,
	.outside_freq_hz = 1000,
	.beep_ms = 200,
	.max_active_ms = 20000,
	.rest_ms = 30000,
	.outside_max_ms = 10000,
	/* zero welfare fields: the firmware's defaults (3 cues, 3 cycles / 24 h) */
};

static long steps, shutoffs, cutoffs;
static enum ev path[DEPTH];
static int reported;

static void report(const char *rule, int depth)
{
	failures++;
	if (reported++) {
		return;
	}
	printf("FAIL %s, after:\n", rule);
	for (int i = 0; i <= depth; i++) {
		printf("  %d. %s\n", i + 1, EV_NAME[path[i]]);
	}
}

static void drain(struct cue *c)
{
	struct episode ep;
	struct welfare_event we;

	while (cue_take_episode(c, &ep)) {
	}
	while (cue_take_welfare(c, &we)) {
	}
}

static void explore(const struct cue *at, int64_t now, int depth)
{
	if (depth == DEPTH) {
		return;
	}
	for (int e = 0; e < EV_N; e++) {
		struct cue c = *at;
		struct cue_command cmd = {0};
		struct geofence_result r = {.margin_m = 20};
		int64_t t = now + 1000;
		bool was_off = c.enforcement_off;

		path[depth] = (enum ev)e;
		switch ((enum ev)e) {
		case EV_DAY:
			t = now + 25LL * 60 * 60 * 1000;
			/* fall through */
		case EV_INSIDE:
			r.state = GEOFENCE_INSIDE;
			cmd = cue_update(&c, &r, 5.0, t);
			break;
		case EV_WARNING:
			r.state = GEOFENCE_WARNING;
			r.margin_m = 2;
			cmd = cue_update(&c, &r, 5.0, t);
			break;
		case EV_OUTSIDE:
			r.state = GEOFENCE_OUTSIDE;
			r.margin_m = -3;
			cmd = cue_update(&c, &r, 5.0, t);
			break;
		case EV_BOUNDARY:
			cue_rearm_at(&c, t);
			break;
		case EV_CARETAKER:
			cue_clear_shutoff_at(&c, t);
			break;
		case EV_MODE:
			cue_set_mode(&c, c.mode == CUE_MODE_AUDIO ? CUE_MODE_TRACK : CUE_MODE_AUDIO);
			break;
		default:
			break;
		}
		drain(&c);
		steps++;
		shutoffs += c.enforcement_off;
		cutoffs += c.pulse_cutoff;

		if (c.enforcement_off && cmd.active) {
			report("R1: a cue sounded while auto shut-off was on", depth);
		}
		if (was_off && !c.enforcement_off && e != EV_CARETAKER) {
			report("R2: shut-off cleared by something other than the caretaker re-arm", depth);
		}
		if (c.outside_cues > 3) {
			report("R3: more than 3 outside cues in one crossing", depth);
		}
		explore(&c, t, depth + 1);
	}
}

int main(void)
{
	struct cue c;

	cue_init(&c, &CFG);
	explore(&c, 0, 0);
	printf("cue explore: %ld steps to depth %d, %ld with shut-off on, %ld with pulse cutoff\n",
	       steps, DEPTH, shutoffs, cutoffs);
	/* Not vacuous: shut-off and pulse cutoff must both be reached */
	CHECK(shutoffs > 0);
	CHECK(cutoffs > 0);
	return test_done("cue explore");
}
