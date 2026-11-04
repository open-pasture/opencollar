/*
 * Signed rearm + persisted shut-off: rearm.json vectors, reboot survival,
 * rearm_seq never lowers, serial rearm, fence change does not clear shut-off.
 */
#include "../../src/app.h"
#include "../../src/report.h"
#include "../../src/welfare_store.h"
#include "json.h"
#include "store_ram.h"
#include "test.h"

#define T_SHUTOFF 1790506800 /* 2026-09-27T11:00:00Z */
#define T_NOW 1790510400     /* 2026-09-27T12:00:00Z */

static const struct cue_config CUE = {
	.warn_freq_hz = 2730,
	.outside_freq_hz = 1000,
	.beep_ms = 300,
	.max_active_ms = 20000,
	.rest_ms = 30000,
	.outside_max_ms = 10000,
};
static const struct geofence_config GCFG = {5.0, 1.0, 10.0};

static uint8_t key[32];
static struct proto_id collar;
static struct jval *vecs;

struct canon_buf {
	char b[4096];
	size_t n;
};

static void canon_sink(void *ctx, const uint8_t *p, size_t n)
{
	struct canon_buf *b = ctx;

	memcpy(b->b + b->n, p, n);
	b->n += n;
}

static void load_vecs(void)
{
	const char *pk;

	vecs = json_load(VECTORS "/rearm.json");
	pk = jstr(vecs, "public_key");
	CHECK(proto_base64_decode(pk, strlen(pk), key, 32) == 32);
	CHECK(proto_id_set(&collar, jstr(vecs, "collar_id"), strlen(jstr(vecs, "collar_id"))));
}

static const struct jval *case_named(const char *name)
{
	const struct jval *cases = jget(vecs, "cases");

	for (size_t c = 0; c < cases->n; c++) {
		if (strcmp(jstr(&cases->items[c], "name"), name) == 0) {
			return &cases->items[c];
		}
	}
	printf("no case %s\n", name);
	exit(2);
}

static int64_t parse_time_field(const struct jval *obj, const char *key, int64_t fallback)
{
	const struct jval *v = jget(obj, key);
	int64_t t;

	if (!v || v->t != J_STR) {
		return fallback;
	}
	CHECK(proto_time_parse(v->str, v->str_len, &t));
	return t;
}

static void test_vectors(void)
{
	const struct jval *cases = jget(vecs, "cases");
	int64_t default_shut = parse_time_field(vecs, "shutoff_at", T_SHUTOFF);
	int64_t default_now = parse_time_field(vecs, "trusted_now", T_NOW);
	uint32_t default_held = (uint32_t)jnum(vecs, "held_rearm_seq");
	int n = 0;

	for (size_t c = 0; c < cases->n; c++) {
		const struct jval *k = &cases->items[c];
		const char *name = jstr(k, "name");
		const struct jval *wire = jget(k, "wire");
		struct rearm_cmd cmd;
		enum reject_code got = rearm_parse(wire->str, wire->str_len, key, &cmd);
		uint32_t held = default_held;
		int64_t shut = default_shut;
		int64_t now = default_now;
		bool has_now = true;
		bool enforcement_off = true;
		bool has_shutoff_at = true;
		const struct jval *held_v = jget(k, "held_rearm_seq");
		const struct jval *shut_v = jget(k, "shutoff_at");
		const struct jval *now_v = jget(k, "trusted_now");
		const struct jval *enf_v = jget(k, "enforcement");
		const struct jval *canon_v = jget(k, "canonical");
		const char *want;

		if (held_v) {
			held = (uint32_t)held_v->num;
		}
		if (shut_v && shut_v->t == J_STR) {
			shut = parse_time_field(k, "shutoff_at", shut);
		}
		if (now_v && now_v->t == J_STR) {
			now = parse_time_field(k, "trusted_now", now);
		}
		if (jbool(k, "no_trusted_time")) {
			has_now = false;
		}
		if (enf_v && enf_v->t == J_STR && strcmp(enf_v->str, "on") == 0) {
			enforcement_off = false;
			has_shutoff_at = false;
		}

		if (got == REJECT_NONE) {
			got = rearm_check(&cmd, &collar, held > 0, held, enforcement_off,
					  has_shutoff_at, shut, has_now, now);
		}

		want = jbool(k, "valid") ? "" : jstr(k, "code");
		CHECK_CASE(strcmp(reject_str(got), want) == 0, name, "got '%s', want '%s'",
			   reject_str(got), want);

		if (canon_v && canon_v->t == J_STR && got != REJECT_BAD_SIG) {
			struct wire_scan sc;
			struct canon_buf buf = {0};

			CHECK_CASE(wire_scan(wire->str, wire->str_len, &sc) == REJECT_NONE, name,
				   "scans");
			wire_canonical(wire->str, &sc, canon_sink, &buf);
			CHECK_CASE(buf.n == canon_v->str_len &&
					   memcmp(buf.b, canon_v->str, buf.n) == 0,
				   name, "canonical bytes differ");
		}
		n++;
	}
	CHECK(n >= 15);
	printf("rearm.json: %d cases\n", n);
}

static void force_shutoff(struct app *a, int64_t utc)
{
	a->cue.enforcement_off = true;
	a->cue.armed = false;
	a->cue.escape_cycles = 3;
	cue_note_shutoff_at(&a->cue, utc);
	a->welfare.enforcement_off = true;
	a->welfare.has_shutoff_at = true;
	a->welfare.shutoff_at = utc;
	a->welfare.escape_cycles = 3;
	CHECK(welfare_store_save(&a->welfare) == 0);
}

static void provision_app(struct app *a, int64_t ms)
{
	char line[512];
	char reply[256];

	app_init(a, &CUE, &GCFG);
	app_boot(a, ms);
	snprintf(line, sizeof(line),
		 "provision {\"v\":1,\"c\":\"col_01J9SIMCOLLAR\",\"h\":\"herd_01J7GOLDEN\","
		 "\"k\":\"0123456789abcdef0123456789abcdef\",\"e\":\"https://farm.example.com/collar/v1\","
		 "\"s\":\"%s\"}",
		 jstr(vecs, "public_key"));
	app_line(a, line, strlen(line), false, ms, reply, sizeof(reply));
	CHECK(strcmp(reply, "ok col_01J9SIMCOLLAR") == 0);
}

static void test_apply_and_persist_across_reboot(void)
{
	struct app a;
	struct slot_ack ack;
	bool has_ack;
	const struct jval *wire = jget(case_named("valid"), "wire");
	char reply[256];
	int64_t ms = 1000;
	struct app_fix_in f = {.valid = true,
			       .lat = 38.125,
			       .lon = -92.405,
			       .accuracy_m = 2,
			       .has_time = true,
			       .utc = T_NOW};
	struct welfare_event we;

	store_ram_reset();
	provision_app(&a, ms);
	force_shutoff(&a, T_SHUTOFF);
	app_fix(&a, &f, ms += 1000);

	CHECK(app_rearm(&a, wire->str, wire->str_len, ms, &ack, &has_ack) == REJECT_NONE);
	CHECK(has_ack && ack.status == ACK_APPLIED && ack.version == 1);
	CHECK(!a.cue.enforcement_off && a.welfare.rearm_seq == 1);

	/* Replay after success is stale */
	CHECK(app_rearm(&a, wire->str, wire->str_len, ms, &ack, &has_ack) == REJECT_STALE);

	/* Shut-off persists across reboot */
	force_shutoff(&a, T_SHUTOFF);
	store_ram_reboot();
	app_init(&a, &CUE, &GCFG);
	app_boot(&a, ms += 1000);
	CHECK(a.cue.enforcement_off && a.cue.has_shutoff_at && a.cue.shutoff_at_s == T_SHUTOFF);
	CHECK(a.welfare.rearm_seq == 1);

	/* Serial rearm clears persisted shut-off, keeps rearm_seq */
	app_line(&a, "rearm", 5, false, ms, reply, sizeof(reply));
	CHECK(strcmp(reply, "ok enforcement on") == 0);
	CHECK(!a.cue.enforcement_off && a.welfare.rearm_seq == 1);
	CHECK(cue_take_welfare(&a.cue, &we));
	CHECK(we.kind == WELFARE_ENFORCEMENT_RESUMED && we.has_by && strcmp(we.by, "serial") == 0);

	store_ram_reboot();
	app_init(&a, &CUE, &GCFG);
	app_boot(&a, ms += 1000);
	CHECK(!a.cue.enforcement_off && a.welfare.rearm_seq == 1);
}

static void test_rearm_seq_never_lowers(void)
{
	struct app a;
	struct slot_ack ack;
	bool has_ack;
	const struct jval *wire1 = jget(case_named("valid"), "wire");
	const struct jval *wire2 = jget(case_named("valid_seq_2"), "wire");
	char line[512];
	char reply[256];
	int64_t ms = 1000;
	struct app_fix_in f = {.valid = true,
			       .lat = 38.125,
			       .lon = -92.405,
			       .accuracy_m = 2,
			       .has_time = true,
			       .utc = T_NOW};

	store_ram_reset();
	provision_app(&a, ms);
	force_shutoff(&a, T_SHUTOFF);
	app_fix(&a, &f, ms += 1000);

	CHECK(app_rearm(&a, wire1->str, wire1->str_len, ms, &ack, &has_ack) == REJECT_NONE);
	CHECK(a.welfare.rearm_seq == 1);

	force_shutoff(&a, T_SHUTOFF);
	CHECK(app_rearm(&a, wire2->str, wire2->str_len, ms, &ack, &has_ack) == REJECT_NONE);
	CHECK(a.welfare.rearm_seq == 2);

	force_shutoff(&a, T_SHUTOFF);
	app_line(&a, "rearm", 5, false, ms, reply, sizeof(reply));
	CHECK(a.welfare.rearm_seq == 2);

	snprintf(line, sizeof(line),
		 "provision {\"v\":1,\"c\":\"col_01J9SIMCOLLAR\",\"h\":\"herd_01J7GOLDEN\","
		 "\"k\":\"0123456789abcdef0123456789abcdef\",\"e\":\"https://farm.example.com/collar/v1\","
		 "\"s\":\"%s\"}",
		 jstr(vecs, "public_key"));
	app_line(&a, line, strlen(line), false, ms, reply, sizeof(reply));
	CHECK(a.welfare.rearm_seq == 2);

	store_ram_reboot();
	app_init(&a, &CUE, &GCFG);
	app_boot(&a, ms += 1000);
	CHECK(a.welfare.rearm_seq == 2);

	force_shutoff(&a, T_SHUTOFF);
	app_fix(&a, &f, ms += 1000);
	CHECK(app_rearm(&a, wire1->str, wire1->str_len, ms, &ack, &has_ack) == REJECT_STALE);
	CHECK(a.welfare.rearm_seq == 2 && a.cue.enforcement_off);

	a.welfare.rearm_seq = 1;
	CHECK(welfare_store_save(&a.welfare) == 0);
	welfare_store_load(&a.welfare);
	CHECK(a.welfare.rearm_seq == 2);
}

static void test_fence_change_does_not_clear_shutoff(void)
{
	struct app a;
	int64_t ms = 1000;
	struct jval *cmds = json_load(VECTORS "/commands.json");
	char line[16384];
	char reply[256];
	const struct jval *cases = jget(cmds, "cases");
	const char *wire = NULL;
	struct app_fix_in f = {.valid = true,
			       .lat = 38.125,
			       .lon = -92.405,
			       .accuracy_m = 2,
			       .has_time = true,
			       .utc = T_NOW};

	store_ram_reset();
	provision_app(&a, ms);
	force_shutoff(&a, T_SHUTOFF);

	for (size_t c = 0; c < cases->n; c++) {
		if (strcmp(jstr(&cases->items[c], "name"), "v0_compact") == 0) {
			wire = jget(&cases->items[c], "wire")->str;
			break;
		}
	}
	CHECK(wire != NULL);
	app_fix(&a, &f, ms += 1000);
	snprintf(line, sizeof(line), "boundary %s", wire);
	app_line(&a, line, strlen(line), false, ms, reply, sizeof(reply));
	CHECK(a.cue.enforcement_off && a.welfare.enforcement_off);
	CHECK(a.cue.has_shutoff_at && a.cue.shutoff_at_s == T_SHUTOFF);
}

static void test_server_rearm_emits_by_server(void)
{
	struct app a;
	struct slot_ack ack;
	bool has_ack;
	const struct jval *wire = jget(case_named("valid"), "wire");
	struct welfare_event we;
	int64_t ms = 1000;
	struct app_fix_in f = {.valid = true,
			       .lat = 38.125,
			       .lon = -92.405,
			       .accuracy_m = 2,
			       .has_time = true,
			       .utc = T_NOW};

	store_ram_reset();
	provision_app(&a, ms);
	force_shutoff(&a, T_SHUTOFF);
	app_fix(&a, &f, ms += 1000);
	CHECK(app_rearm(&a, wire->str, wire->str_len, ms, &ack, &has_ack) == REJECT_NONE);
	CHECK(cue_take_welfare(&a.cue, &we));
	CHECK(we.kind == WELFARE_ENFORCEMENT_RESUMED && we.has_by && strcmp(we.by, "server") == 0);
	CHECK(we.rearm_seq == 1);
}

static void test_report_welfare_encode(void)
{
	struct report_welfare w = {
		.enforcement_off = true,
		.has_shutoff_at = true,
		.shutoff_at = T_SHUTOFF,
		.escape_cycles = 3,
		.rearm_seq = 4,
	};
	char buf[256];
	int n = report_encode_welfare(&w, buf, sizeof(buf));
	struct welfare_event ev;
	char evbuf[256];
	int en;
	bool found = false;

	memset(&ev, 0, sizeof(ev));
	ev.kind = WELFARE_ENFORCEMENT_RESUMED;
	ev.has_by = true;
	memcpy(ev.by, "server", 6);
	ev.rearm_seq = 4;

	CHECK(n > 0);
	CHECK(strstr(buf, "\"enforcement\":\"off\"") != NULL);
	CHECK(strstr(buf, "\"escape_cycles\":3") != NULL);
	CHECK(strstr(buf, "\"rearm_seq\":4") != NULL);
	CHECK(strstr(buf, "\"shutoff_at\":\"2026-09-27T11:00:00Z\"") != NULL);
	CHECK(strstr(buf, "\"cycles\"") == NULL);

	en = report_encode_welfare_event(&ev, true, T_NOW, evbuf, sizeof(evbuf));
	CHECK(en > 0);
	CHECK(strstr(evbuf, "\"by\":\"server\"") != NULL);
	CHECK(strstr(evbuf, "\"rearm_seq\":4") != NULL);

	for (size_t i = 0; i < REPORT_CAPS_N; i++) {
		if (strcmp(REPORT_CAPS[i], "rearm") == 0) {
			found = true;
		}
	}
	CHECK(found);
}

int main(void)
{
	load_vecs();
	test_vectors();
	test_apply_and_persist_across_reboot();
	test_rearm_seq_never_lowers();
	test_fence_change_does_not_clear_shutoff();
	test_server_rearm_emits_by_server();
	test_report_welfare_encode();
	printf("ok\n");
	return 0;
}
