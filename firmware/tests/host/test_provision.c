/* Provisioning over the console: a valid payload is stored and wipes the slots; each bad field is its error */
#include "../../src/app.h"
#include "json.h"
#include "store_ram.h"
#include "test.h"

#define T0 1790510400

static struct app a;
static char reply[512];
static char line[16384];
static const char *server_key; /* The vectors' public key */

static const struct cue_config CUE = {2730, 1000, 300, 20000, 30000, 10000};
static const struct geofence_config GCFG = {5.0, 1.0, 10.0};

static void boot(void)
{
	app_init(&a, &CUE, &GCFG);
	app_boot(&a, 0);
}

static const char *say(const char *text)
{
	app_line(&a, text, strlen(text), false, 1000, reply, sizeof(reply));
	return reply;
}

static const char *provision(const char *c, const char *h, const char *k, const char *e,
			     const char *s)
{
	snprintf(line, sizeof(line), "provision {\"v\":1,\"c\":\"%s\",\"h\":\"%s\",\"k\":\"%s\",\"e\":\"%s\",\"s\":\"%s\"}",
		 c, h, k, e, s);
	return say(line);
}

#define KEY "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
#define URL "https://farm.example.com/collar/v1"

static void fix_at(int64_t utc)
{
	struct app_fix_in f = {.valid = true, .lat = 38.125, .lon = -92.405, .accuracy_m = 2,
			       .has_time = true, .utc = utc};

	app_fix(&a, &f, 2000);
}

static void test_valid_payload_is_stored_and_wipes_slots(void)
{
	struct jval *f = json_load(VECTORS "/commands.json");
	const struct jval *cases = jget(f, "cases");
	const struct jval *wire = NULL;

	for (size_t c = 0; c < cases->n; c++) {
		if (strcmp(jstr(&cases->items[c], "name"), "v0_compact") == 0) {
			wire = jget(&cases->items[c], "wire");
		}
	}
	server_key = jstr(f, "public_key");

	store_ram_reset();
	boot();
	CHECK(strcmp(say("status"), "unprovisioned fw 0.2.0") == 0);
	snprintf(line, sizeof(line), "boundary %s", wire->str);
	CHECK(strcmp(say(line), "error unprovisioned") == 0);

	CHECK(strcmp(provision("col_1", "herd_01J7GOLDEN", KEY, URL, server_key), "ok col_1") == 0);
	CHECK(strcmp(say("status"),
		     "collar col_1 herd herd_01J7GOLDEN fw 0.2.0 config - active - slots -") == 0);

	/* A boundary for this herd applies once the collar has GNSS time past it */
	fix_at(T0 + 60);
	snprintf(line, sizeof(line), "boundary %s", wire->str);
	CHECK(strcmp(say(line), "applied 57") == 0);
	CHECK(a.fence != NULL && a.fence->version == 57);
	CHECK(strcmp(say("status"),
		     "collar col_1 herd herd_01J7GOLDEN fw 0.2.0 config - active 57 slots 57") == 0);

	/* Kept over a reboot */
	store_ram_reboot();
	boot();
	CHECK(a.prov.ok && strcmp(a.prov.collar_id.s, "col_1") == 0);
	CHECK(strcmp(a.prov.endpoint, URL) == 0 && strcmp(a.prov.key, KEY) == 0);
	CHECK(a.fence != NULL && a.fence->version == 57 && a.acks.n == 1);

	/* Provisioning again wipes slots, config and pending acks */
	CHECK(strcmp(provision("col_2", "herd_2", KEY, URL, server_key), "ok col_2") == 0);
	CHECK(a.fence == NULL && a.slots.n == 0 && a.acks.n == 0);
	CHECK(strcmp(say("status"), "collar col_2 herd herd_2 fw 0.2.0 config - active - slots -") ==
	      0);
	store_ram_reboot();
	boot();
	CHECK(a.prov.ok && strcmp(a.prov.collar_id.s, "col_2") == 0 && a.fence == NULL &&
	      a.slots.n == 0 && a.acks.n == 0);

	/* The old herd's boundary is now another herd's */
	fix_at(T0 + 120);
	snprintf(line, sizeof(line), "boundary %s", wire->str);
	CHECK(strcmp(say(line), "rejected 57 wrong_herd") == 0);
}

static void expect_error(const char *what, const char *got, const char *code)
{
	char want[64];

	snprintf(want, sizeof(want), "error %s", code);
	CHECK_CASE(strcmp(got, want) == 0, what, "got '%s', want '%s'", got, want);
	/* Nothing changed */
	CHECK_CASE(a.prov.ok && strcmp(a.prov.collar_id.s, "col_2") == 0, what, "provisioning kept");
}

static void test_each_bad_field(void)
{
	char long_id[80], long_key[140], long_url[300];

	memset(long_id, 'x', 65);
	long_id[65] = '\0';
	memset(long_key, 'k', 129);
	long_key[129] = '\0';
	snprintf(long_url, sizeof(long_url), "https://%0249d", 0); /* 257 bytes */

	expect_error("not json", say("provision hello"), "bad_json");
	expect_error("empty", say("provision"), "bad_json");
	expect_error("nested", say("provision {\"v\":1,\"c\":{\"a\":1}}"), "bad_json");
	expect_error("v 2",
		     say("provision {\"v\":2,\"c\":\"c\",\"h\":\"h\",\"k\":\"" KEY "\",\"e\":\"" URL
			 "\",\"s\":\"x\"}"),
		     "bad_version");
	expect_error("v missing", say("provision {\"c\":\"c\"}"), "bad_version");
	expect_error("v string", say("provision {\"v\":\"1\"}"), "bad_version");
	expect_error("c missing", say("provision {\"v\":1,\"h\":\"h\"}"), "bad_collar_id");
	expect_error("c empty", provision("", "h", KEY, URL, server_key), "bad_collar_id");
	expect_error("c 65 bytes", provision(long_id, "h", KEY, URL, server_key), "bad_collar_id");
	expect_error("c number", say("provision {\"v\":1,\"c\":5}"), "bad_collar_id");
	expect_error("h empty", provision("c", "", KEY, URL, server_key), "bad_herd_id");
	expect_error("h 65 bytes", provision("c", long_id, KEY, URL, server_key), "bad_herd_id");
	expect_error("k short", provision("c", "h", "0123456789abcde", URL, server_key), "bad_key");
	expect_error("k long", provision("c", "h", long_key, URL, server_key), "bad_key");
	expect_error("k space", provision("c", "h", "0123456789 abcdef", URL, server_key), "bad_key");
	expect_error("e http", provision("c", "h", KEY, "http://farm.example.com/collar/v1", server_key),
		     "bad_endpoint");
	expect_error("e bare", provision("c", "h", KEY, "https://", server_key), "bad_endpoint");
	expect_error("e 257 bytes", provision("c", "h", KEY, long_url, server_key), "bad_endpoint");
	expect_error("s not base64", provision("c", "h", KEY, URL, "not base64!"), "bad_server_key");
	expect_error("s 31 bytes",
		     provision("c", "h", KEY, URL, "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHg=="),
		     "bad_server_key");
	expect_error("s 33 bytes",
		     provision("c", "h", KEY, URL, "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8g"),
		     "bad_server_key");
	expect_error("s missing",
		     say("provision {\"v\":1,\"c\":\"c\",\"h\":\"h\",\"k\":\"" KEY "\",\"e\":\"" URL "\"}"),
		     "bad_server_key");

	/* Unknown keys are ignored; the payload is taken as the scanner types it */
	snprintf(line, sizeof(line),
		 "provision  {\"v\":1, \"c\":\"col_3\", \"h\":\"herd_3\", \"k\":\"%s\", \"e\":\"%s\", "
		 "\"s\":\"%s\", \"label\":\"Cow 214\"}  ",
		 KEY, URL, server_key);
	CHECK(strcmp(say(line), "ok col_3") == 0);
}

static void test_lines(void)
{
	CHECK(strcmp(say("  status  "), "collar col_3 herd herd_3 fw 0.2.0 config - active - slots -") ==
	      0);
	CHECK(strcmp(say(""), "") == 0);
	CHECK(strcmp(say("   "), "") == 0);
	CHECK(strcmp(say("statusx"), "error unknown_command") == 0);
	CHECK(strcmp(say("status now"), "error unknown_command") == 0);
	CHECK(strcmp(say("reboot"), "error unknown_command") == 0);
	app_line(&a, "provision {", 11, true, 0, reply, sizeof(reply));
	CHECK(strcmp(reply, "error too_long") == 0);
	app_line(&a, "boundary {", 10, true, 0, reply, sizeof(reply));
	CHECK(strcmp(reply, "error too_large") == 0);
}

int main(void)
{
	test_valid_payload_is_stored_and_wipes_slots();
	test_each_bad_field();
	test_lines();
	return test_done("provision");
}
