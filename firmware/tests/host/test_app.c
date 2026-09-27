/*
 * The collar end to end on the host: provision, boundaries staged and
 * applied on GNSS time, cues, a collar-scoped track-mode boundary with holes,
 * a reboot in the middle, config, pending acks.
 */
#include "../../src/app.h"
#include "json.h"
#include "store_ram.h"
#include "test.h"

#define T0 1790510400    /* 2026-09-27T12:00:00Z: v57's effective_at */
#define T1230 1790512200 /* 12:30: v58's effective_at */

static struct app a;
static char reply[512];
static char line[16384];
static struct jval *cmds, *cfgs;
static int64_t ms;

static const struct cue_config CUE = {2730, 1000, 300, 20000, 30000, 10000};
static const struct geofence_config GCFG = {5.0, 1.0, 10.0};

static const struct jval *wire_of(struct jval *f, const char *name)
{
	const struct jval *cases = jget(f, "cases");

	for (size_t c = 0; c < cases->n; c++) {
		if (strcmp(jstr(&cases->items[c], "name"), name) == 0) {
			return jget(&cases->items[c], "wire");
		}
	}
	printf("no case %s\n", name);
	exit(2);
}

static const char *say(const char *text)
{
	app_line(&a, text, strlen(text), false, ms, reply, sizeof(reply));
	return reply;
}

static const char *send(const char *verb, struct jval *f, const char *name)
{
	snprintf(line, sizeof(line), "%s %s", verb, wire_of(f, name)->str);
	return say(line);
}

static struct app_fix_out fix(double lat, double lon, int64_t utc)
{
	struct app_fix_in f = {.valid = true, .lat = lat, .lon = lon, .accuracy_m = 2,
			       .has_time = true, .utc = utc};

	ms += 1000;
	return app_fix(&a, &f, ms);
}

static void boot(void)
{
	app_init(&a, &CUE, &GCFG);
	app_boot(&a, ms);
}

int main(void)
{
	cmds = json_load(VECTORS "/commands.json");
	cfgs = json_load(VECTORS "/config.json");
	store_ram_reset();
	boot();

	snprintf(line, sizeof(line),
		 "provision {\"v\":1,\"c\":\"col_01J9SIMCOLLAR\",\"h\":\"herd_01J7GOLDEN\","
		 "\"k\":\"0123456789abcdef0123456789abcdef\",\"e\":\"https://farm.example.com/collar/v1\","
		 "\"s\":\"%s\"}",
		 jstr(cmds, "public_key"));
	CHECK(strcmp(say(line), "ok col_01J9SIMCOLLAR") == 0);

	/* No boundary: fixes, no fence, no cues */
	struct app_fix_out o = fix(38.125, -92.405, T0 - 120);

	CHECK(!o.fenced && !o.cmd.active);

	/* v57 (effective 12:00) arrives at 11:58 GNSS time: staged */
	CHECK(strcmp(send("boundary", cmds, "v0_compact"), "received 57") == 0);
	CHECK(a.fence == NULL);
	CHECK(strcmp(say("status"), "collar col_01J9SIMCOLLAR herd herd_01J7GOLDEN fw 0.2.0 config - "
				    "active - slots 57") == 0);
	/* The same command again: re-acked as received */
	CHECK(strcmp(send("boundary", cmds, "v0_compact"), "received 57") == 0);

	o = fix(38.125, -92.405, T0 - 1);
	CHECK(!o.applied && !o.fenced);
	/* The first fix at 12:00 applies it, acked at that fix's time */
	o = fix(38.125, -92.405, T0);
	CHECK(o.applied && o.ack.version == 57 && o.ack.status == ACK_APPLIED && o.ack.has_at &&
	      o.ack.at == T0);
	CHECK(o.fenced && o.version == 57 && o.r.state == GEOFENCE_INSIDE && !o.cmd.active);

	/* Walk south to the edge at 38.12: warning cues, then the crossing */
	double lat = 38.125;
	int warn = 0, outside = 0;

	for (int i = 0; i < 700; i++) {
		lat -= 0.00001; /* ~1.1 m a step */
		o = fix(lat, -92.405, T0 + 1 + i);
		warn += o.cmd.active && o.cmd.kind == CUE_WARN;
		outside += o.cmd.active && o.cmd.kind == CUE_OUTSIDE;
		if (o.r.state == GEOFENCE_OUTSIDE) {
			break;
		}
	}
	CHECK(warn >= 3 && outside == 1);

	struct episode e;

	CHECK(cue_take_episode(&a.cue, &e) && e.outcome == EPISODE_CROSSED && e.ring == 0);

	/* A tampered command: rejected, and acked with what could be read */
	CHECK(strcmp(send("boundary", cmds, "tampered_version"), "rejected 59 bad_sig") == 0);

	/* v58: this collar's own, with two holes, track mode, effective 12:30 */
	CHECK(strcmp(send("boundary", cmds, "holes_collar_id_track"), "received 58") == 0);
	CHECK(a.fence->version == 57);

	/* Reboot before 12:30: v57 is enforced at once, v58 waits for a fix */
	store_ram_reboot();
	boot();
	CHECK(a.fence != NULL && a.fence->version == 57 && !a.has_clock);
	CHECK(strcmp(say("status"), "collar col_01J9SIMCOLLAR herd herd_01J7GOLDEN fw 0.2.0 config - "
				    "active 57 slots 57 58") == 0);
	/* received 57 twice, applied 57, rejected 59, received 58 */
	CHECK(a.acks.n == 5);
	CHECK(a.acks.q[3].version == 59 && a.acks.q[3].code == REJECT_BAD_SIG);

	/* An older boundary now is stale */
	CHECK(strcmp(send("boundary", cmds, "exponent_1e-7"), "rejected 4 stale") == 0);

	/* Offline past 12:30, the first fix applies v58 at its own time */
	o = fix(42.0304, -93.6180, T1230 + 300);
	CHECK(o.applied && o.ack.version == 58 && o.ack.at == T1230 + 300);
	CHECK(a.fence->version == 58 && a.fence->rings == 3 && a.cue.mode == CUE_MODE_TRACK);

	/* Track mode: the fence runs, nothing sounds, even walking into a hole */
	int sounds = 0, states_out = 0;

	for (int i = 0; i < 400; i++) {
		o = fix(42.03 + i * 0.00001, -93.6180, T1230 + 301 + i);
		sounds += o.cmd.active;
		states_out += o.r.state == GEOFENCE_OUTSIDE;
	}
	CHECK(sounds == 0 && states_out > 0);
	CHECK(!cue_take_episode(&a.cue, &e));

	/* Config: fast cadence until 13:10 by GNSS time */
	CHECK(strcmp(send("config", cfgs, "valid_full"), "ok 3") == 0);
	uint32_t r, p;
	int64_t now;

	CHECK(app_now(&a, ms, &now));
	config_cadence(&a.cfg, true, now, &r, &p);
	CHECK(r == 10 && p == 10);
	config_cadence(&a.cfg, true, 1790514600, &r, &p);
	CHECK(r == 60 && p == 60);
	CHECK(strcmp(send("config", cfgs, "valid_full"), "error stale") == 0);
	CHECK(strcmp(send("config", cfgs, "wrong_collar"), "error wrong_collar") == 0);

	/* Everything survives a reboot */
	store_ram_reboot();
	boot();
	CHECK(a.fence->version == 58 && a.cue.mode == CUE_MODE_TRACK && a.cfg.version == 3);
	CHECK(strcmp(say("status"), "collar col_01J9SIMCOLLAR herd herd_01J7GOLDEN fw 0.2.0 config 3 "
				    "active 58 slots 58") == 0);

	return test_done("app");
}
