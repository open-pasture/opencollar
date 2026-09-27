/* Config commands: config.json, fast mode by GNSS time, endpoint fallback, persistence */
#include "../../src/config.h"
#include "../../src/store.h"
#include "json.h"
#include "store_ram.h"
#include "test.h"

#define T0 1790510400 /* 2026-09-27T12:00:00Z */
#define FAST_UNTIL 1790514600 /* 2026-09-27T13:10:00Z, as in the vectors */

static uint8_t key[32];
static struct proto_id collar;
static const char *base = "https://farm.example.com/collar/v1";

static const struct jval *cases_of(struct jval *f)
{
	const char *pk = jstr(f, "public_key");

	CHECK(proto_base64_decode(pk, strlen(pk), key, 32) == 32);
	CHECK(proto_id_set(&collar, jstr(f, "collar_id"), strlen(jstr(f, "collar_id"))));
	return jget(f, "cases");
}

static const struct jval *find(const struct jval *cases, const char *name)
{
	for (size_t c = 0; c < cases->n; c++) {
		if (strcmp(jstr(&cases->items[c], "name"), name) == 0) {
			return jget(&cases->items[c], "wire");
		}
	}
	printf("no case %s\n", name);
	exit(2);
}

static void test_vectors(void)
{
	struct jval *f = json_load(VECTORS "/config.json");
	const struct jval *cases = cases_of(f);
	uint32_t held = (uint32_t)jnum(f, "held_version");
	int n = 0;

	for (size_t c = 0; c < cases->n; c++) {
		const struct jval *k = &cases->items[c];
		const char *name = jstr(k, "name");
		const struct jval *wire = jget(k, "wire");
		struct config_cmd cmd;
		enum reject_code got = config_parse(wire->str, wire->str_len, key, &cmd);

		if (got == REJECT_NONE) {
			got = config_check(&cmd, &collar, true, held);
		}

		const char *want = jbool(k, "valid") ? "" : jstr(k, "code");

		CHECK_CASE(strcmp(reject_str(got), want) == 0, name, "got '%s', want '%s'",
			   reject_str(got), want);
		n++;
	}
	CHECK(n >= 15);
	printf("config.json: %d cases\n", n);
}

static void test_fast_mode_expires_by_gnss_time(void)
{
	struct jval *f = json_load(VECTORS "/config.json");
	const struct jval *wire = find(cases_of(f), "valid_full");
	struct config c;
	uint32_t r, p;

	store_ram_reset();
	config_init(&c);
	config_cadence(&c, false, 0, &r, &p);
	CHECK(r == 60 && p == 60); /* No config: 60 s */

	CHECK(config_receive(&c, wire->str, wire->str_len, key, &collar, base, true, T0) ==
	      REJECT_NONE);
	CHECK(c.has && c.version == 3 && c.has_herd && strcmp(c.herd.s, "herd_01J7GOLDEN") == 0);

	config_cadence(&c, true, FAST_UNTIL - 1, &r, &p);
	CHECK(r == 10 && p == 10);
	config_cadence(&c, true, FAST_UNTIL, &r, &p);
	CHECK(r == 60 && p == 60); /* Back to base with no further command */
	config_cadence(&c, true, FAST_UNTIL + 3600, &r, &p);
	CHECK(r == 60 && p == 60);
	/* Without GNSS time since boot the collar can't know: base */
	config_cadence(&c, false, 0, &r, &p);
	CHECK(r == 60 && p == 60);

	/* A minimal config has no fast mode */
	struct config m;

	config_init(&m);
	wire = find(cases_of(f), "valid_minimal");
	CHECK(config_receive(&m, wire->str, wire->str_len, key, &collar, base, true, T0) ==
	      REJECT_NONE);
	config_cadence(&m, true, T0, &r, &p);
	CHECK(r == 60 && p == 60 && !m.has_herd);
	CHECK(strcmp(config_endpoint(&m, base), base) == 0);
}

static void test_persisted_and_stale(void)
{
	struct jval *f = json_load(VECTORS "/config.json");
	const struct jval *cases = cases_of(f);
	const struct jval *full = find(cases, "valid_full");
	struct config c, again;

	store_ram_reset();
	config_init(&c);
	CHECK(config_receive(&c, full->str, full->str_len, key, &collar, base, true, T0) ==
	      REJECT_NONE);

	/* After a reboot it is still in force */
	store_ram_reboot();
	config_load(&again);
	CHECK(again.has && again.version == 3 && again.report_s == 60 && again.has_fast &&
	      again.fast_until == FAST_UNTIL && strcmp(again.herd.s, "herd_01J7GOLDEN") == 0);

	/* The same version again, or a lower one, is stale; reported once as config_reject */
	CHECK(config_receive(&again, full->str, full->str_len, key, &collar, base, true, T0) ==
	      REJECT_STALE);
	CHECK(again.has_reject && again.reject_version == 3 && again.reject_code == REJECT_STALE);
	const struct jval *low = find(cases, "stale_lower");

	CHECK(config_receive(&again, low->str, low->str_len, key, &collar, base, true, T0) ==
	      REJECT_STALE);
	CHECK(again.reject_version == 1);

	/* A rejected config changes nothing */
	const struct jval *bad = find(cases, "report_s_9");
	struct config fresh;

	config_init(&fresh);
	CHECK(config_receive(&fresh, bad->str, bad->str_len, key, &collar, base, true, T0) ==
	      REJECT_BAD_CONFIG);
	CHECK(!fresh.has && fresh.report_s == 60 && fresh.reject_code == REJECT_BAD_CONFIG);

	/* Tampered: bad_sig, version read best effort */
	const struct jval *tampered = find(cases, "tampered_herd_id");

	CHECK(config_receive(&fresh, tampered->str, tampered->str_len, key, &collar, base, true,
			     T0) == REJECT_BAD_SIG);
	CHECK(!fresh.has_herd && fresh.reject_version == 3);

	/* Corrupt the stored config: it reads as none */
	CHECK(store_ram_corrupt(STORE_ID_CONFIG, 10));
	config_load(&again);
	CHECK(!again.has && again.report_s == 60);

	config_wipe(&c);
	config_load(&again);
	CHECK(!again.has);
}

static void test_endpoint_fallback(void)
{
	struct jval *f = json_load(VECTORS "/config.json");
	const struct jval *full = find(cases_of(f), "valid_full");
	const char *old = "https://old.example.com/collar/v1";
	const char *fresh = "https://farm.example.com/collar/v1"; /* The vector's endpoint */
	struct config c, again;

	/* The new endpoint works: the first successful report there makes it the endpoint */
	store_ram_reset();
	config_init(&c);
	CHECK(config_receive(&c, full->str, full->str_len, key, &collar, old, true, T0) ==
	      REJECT_NONE);
	CHECK(c.trying && strcmp(config_endpoint(&c, old), fresh) == 0);
	config_report_result(&c, false, true, T0 + 60);
	CHECK(c.trying);
	config_report_result(&c, true, true, T0 + 120);
	CHECK(!c.trying && c.has_endpoint && strcmp(config_endpoint(&c, old), fresh) == 0);
	config_load(&again);
	CHECK(strcmp(config_endpoint(&again, old), fresh) == 0);

	/* The new endpoint fails for 24 h: back to the previous one */
	store_ram_reset();
	config_init(&c);
	CHECK(config_receive(&c, full->str, full->str_len, key, &collar, old, true, T0) ==
	      REJECT_NONE);
	config_report_result(&c, false, true, T0 + 3600);
	config_report_result(&c, false, true, T0 + 86399);
	CHECK(c.trying && strcmp(config_endpoint(&c, old), fresh) == 0);
	/* A reboot during the trial keeps it, and its start time */
	config_load(&again);
	CHECK(again.trying && again.trial_since == T0);
	config_report_result(&again, false, true, T0 + 86400);
	CHECK(!again.trying && strcmp(config_endpoint(&again, old), old) == 0);
	config_load(&c);
	CHECK(!c.trying && strcmp(config_endpoint(&c, old), old) == 0);

	/* No GNSS time when the config arrived: the trial clock starts at the first failure */
	store_ram_reset();
	config_init(&c);
	CHECK(config_receive(&c, full->str, full->str_len, key, &collar, old, false, 0) ==
	      REJECT_NONE);
	config_report_result(&c, false, false, 0);
	CHECK(c.trying && !c.has_trial_since);
	config_report_result(&c, false, true, T0);
	CHECK(c.has_trial_since && c.trial_since == T0);
	config_report_result(&c, false, true, T0 + 86400);
	CHECK(!c.trying);

	/* The endpoint it already uses: nothing to try */
	store_ram_reset();
	config_init(&c);
	CHECK(config_receive(&c, full->str, full->str_len, key, &collar, fresh, true, T0) ==
	      REJECT_NONE);
	CHECK(!c.trying && strcmp(config_endpoint(&c, fresh), fresh) == 0);
}

int main(void)
{
	test_vectors();
	test_fast_mode_expires_by_gnss_time();
	test_persisted_and_stale();
	test_endpoint_fallback();
	return test_done("config");
}
