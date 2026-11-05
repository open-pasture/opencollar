/*
 * SPDX-License-Identifier: Apache-2.0
 *
 * Welfare hook honors shut-off-until-caretaker-re-arm (PR #22).
 * Fence cue_rearm must not clear shut-off; cue_clear_shutoff does.
 * Numeric caps: see test_welfare_caps.c (PR #2 WELFARE_DEFAULT_*).
 */
#include "test.h"

#include "cue.h"
#include "welfare.h"

#include <string.h>

int main(void)
{
	struct cue_config cfg = {0};
	struct cue c;
	struct welfare_hooks wh;
	struct geofence_result geo = {0};
	struct cue_command cmd = {0};
	struct cue_command out;

	cfg.warn_freq_hz = 2700;
	cfg.outside_freq_hz = 3200;
	cfg.beep_ms = 200;
	cfg.max_active_ms = 20000;
	cfg.rest_ms = 30000;
	cfg.outside_max_ms = 10000;
	/* Disable cycle limit so we can force shut-off manually. */
	cfg.max_outside_cues = 255;
	cfg.escape_cycle_limit = 255;
	cfg.escape_cycle_window_ms = UINT32_MAX;

	cue_init(&c, &cfg);
	welfare_hooks_init_shutoff(&wh, &c);

	cmd.active = true;
	cmd.kind = CUE_WARN;
	cmd.freq_hz = 2700;
	cmd.volume = 2;
	cmd.duration_ms = 200;

	/* Not shut off → pass through */
	out = welfare_apply(&wh, cmd, &geo, 1000);
	CHECK(out.active);
	CHECK(out.kind == CUE_WARN);

	/* Force shut-off */
	c.enforcement_off = true;
	out = welfare_apply(&wh, cmd, &geo, 2000);
	CHECK(!out.active);
	CHECK(out.kind == CUE_NONE);

	/* Fence rearm does NOT clear shut-off */
	cue_rearm_at(&c, 3000);
	CHECK(c.enforcement_off);
	out = welfare_apply(&wh, cmd, &geo, 3000);
	CHECK(!out.active);

	/* Caretaker clear resumes */
	cue_clear_shutoff_at(&c, 4000);
	CHECK(!c.enforcement_off);
	out = welfare_apply(&wh, cmd, &geo, 4000);
	CHECK(out.active);
	CHECK(out.kind == CUE_WARN);

	return test_done("welfare_shutoff");
}
