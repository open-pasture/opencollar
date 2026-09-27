/*
 * A herd change through the app, with commands signed here by the vectors'
 * key (seed 00 01 .. 1f):
 * - the signed config naming herd B drops herd A's staged boundaries, and
 *   herd A's fence stays in force until one of herd B's applies;
 * - herd B's boundary refused `wrong_herd` before the config arrived is taken
 *   when it is offered again after it, and so is one of herd B's below the
 *   dropped versions (`have` went back down to the active version);
 * - a power cut at any byte of the change leaves herd A with its slots or
 *   herd B without them.
 */
#include "../../src/app.h"
#include "monocypher-ed25519.h"
#include "store_ram.h"
#include "test.h"

#define T0 1790510400 /* 2026-09-27T12:00:00Z */

#define COLLAR "col_01J9SIMCOLLAR"
#define HERD_A "herd_01J7GOLDEN"
#define HERD_B "herd_01J7OTHER"

#define OLD_STATUS "collar " COLLAR " herd " HERD_A " fw 0.2.0 config - active 10 slots 10 13"
#define NEW_STATUS "collar " COLLAR " herd " HERD_B " fw 0.2.0 config 1 active 10 slots 10"

static struct app a;
static char reply[512];
static char line[2048];
static int64_t ms;
static uint8_t secret[64], public[32];
static struct store_ram_image before;

static const struct cue_config CUE = {2730, 1000, 300, 20000, 30000, 10000};
static const struct geofence_config GCFG = {5.0, 1.0, 10.0};

static void base64(const uint8_t *in, size_t n, char *out)
{
	static const char abc[] =
		"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
	size_t o = 0;

	for (size_t i = 0; i < n; i += 3) {
		uint32_t v = (uint32_t)in[i] << 16 | (i + 1 < n ? (uint32_t)in[i + 1] << 8 : 0) |
			     (i + 2 < n ? in[i + 2] : 0);

		out[o++] = abc[v >> 18 & 63];
		out[o++] = abc[v >> 12 & 63];
		out[o++] = i + 1 < n ? abc[v >> 6 & 63] : '=';
		out[o++] = i + 2 < n ? abc[v & 63] : '=';
	}
	out[o] = '\0';
}

static const char *say(const char *text)
{
	app_line(&a, text, strlen(text), false, ms, reply, sizeof(reply));
	return reply;
}

/* body: canonical JSON (keys sorted, compact); signed, then sent as `verb` */
static const char *send_signed(const char *verb, const char *body)
{
	uint8_t sig[64];
	char sig64[89];
	size_t n = strlen(body);

	crypto_ed25519_sign(sig, secret, (const uint8_t *)body, n);
	base64(sig, sizeof(sig), sig64);
	snprintf(line, sizeof(line), "%s %.*s,\"sig\":\"%s\"}", verb, (int)(n - 1), body, sig64);
	return say(line);
}

/* A 0.01 degree square of `herd` with its west edge at lon; eff 0: immediate */
static const char *boundary(uint32_t version, const char *herd, double lon, int64_t eff)
{
	char body[512], when[64] = "", t[24];

	if (eff) {
		proto_time_format(eff, t, sizeof(t));
		snprintf(when, sizeof(when), "\"effective_at\":\"%s\",", t);
	}
	snprintf(body, sizeof(body),
		 "{\"boundary\":[[%.2f,38.12],[%.2f,38.12],[%.2f,38.13],[%.2f,38.13]],"
		 "\"command_id\":\"bnd_%u\",%s\"herd_id\":\"%s\",\"version\":%u}",
		 lon, lon + 0.01, lon + 0.01, lon, (unsigned)version, when, herd,
		 (unsigned)version);
	return send_signed("boundary", body);
}

static const char *config(uint32_t version, const char *herd)
{
	char body[256];

	snprintf(body, sizeof(body),
		 "{\"collar_id\":\"" COLLAR "\",\"command_id\":\"cfg_%u\",\"herd_id\":\"%s\","
		 "\"poll_s\":60,\"report_s\":60,\"version\":%u}",
		 (unsigned)version, herd, (unsigned)version);
	return send_signed("config", body);
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

static void test_herd_change(void)
{
	char pk64[45];
	struct app_fix_out o;

	base64(public, sizeof(public), pk64);
	store_ram_reset();
	boot();
	snprintf(line, sizeof(line),
		 "provision {\"v\":1,\"c\":\"" COLLAR "\",\"h\":\"" HERD_A "\","
		 "\"k\":\"0123456789abcdef0123456789abcdef\","
		 "\"e\":\"https://farm.example.com/collar/v1\",\"s\":\"%s\"}",
		 pk64);
	CHECK(strcmp(say(line), "ok " COLLAR) == 0);
	fix(38.125, -92.405, T0 - 600); /* GNSS time 11:50 */

	/* Herd A's fence, and herd A's next strip for 12:00 */
	CHECK(strcmp(boundary(10, HERD_A, -92.41, 0), "applied 10") == 0);
	CHECK(strcmp(boundary(13, HERD_A, -92.40, T0), "received 13") == 0);
	/* The server moved the collar to herd B and sent herd B's boundary; the
	 * collar polled before a report brought the config naming herd B */
	CHECK(strcmp(boundary(14, HERD_B, -92.38, 0), "rejected 14 wrong_herd") == 0);
	CHECK(strcmp(say("status"), OLD_STATUS) == 0);
	store_ram_save(&before);

	/* The config: herd A's strip goes, herd A's fence stays */
	CHECK(strcmp(config(1, HERD_B), "ok 1") == 0);
	CHECK(strcmp(say("status"), NEW_STATUS) == 0);
	CHECK(a.fence && a.fence->version == 10);

	/* 12:00 passes out of coverage: nothing of herd A's applies */
	o = fix(38.125, -92.405, T0);
	CHECK(!o.applied && o.fenced && o.version == 10);

	/* A reboot: the same */
	store_ram_reboot();
	boot();
	CHECK(a.fence && a.fence->version == 10);
	CHECK(strcmp(say("status"), NEW_STATUS) == 0);
	o = fix(38.125, -92.405, T0 + 60);
	CHECK(!o.applied && o.fenced && o.version == 10);

	/* Herd B's boundary below the dropped strip's version is not stale */
	CHECK(strcmp(boundary(12, HERD_B, -92.38, 0), "applied 12") == 0);
	/* The one refused before the config, offered again */
	CHECK(strcmp(boundary(14, HERD_B, -92.38, 0), "applied 14") == 0);
	CHECK(a.fence && a.fence->version == 14);
	CHECK(strcmp(boundary(13, HERD_A, -92.40, T0), "rejected 13 wrong_herd") == 0);
}

/* The change with the power cut after every byte it writes */
static void test_power_cut(void)
{
	size_t w0, total;
	int olds = 0, news = 0;

	store_ram_load(&before);
	boot();
	w0 = store_ram_written();
	CHECK(strcmp(config(1, HERD_B), "ok 1") == 0);
	total = store_ram_written() - w0;

	for (size_t cut = 0; cut <= total; cut++) {
		store_ram_load(&before);
		boot();
		store_ram_cut_after((long)cut);
		config(1, HERD_B);
		store_ram_reboot();
		boot();
		say("status");
		if (strcmp(reply, OLD_STATUS) == 0) {
			olds++;
		} else if (strcmp(reply, NEW_STATUS) == 0) {
			news++;
		} else {
			CHECK_CASE(false, "herd change", "cut after %zu of %zu bytes: '%s'", cut,
				   total, reply);
		}
		CHECK(a.fence && a.fence->version == 10);
	}
	CHECK(olds > 0 && news > 0);
	printf("herd change: %zu bytes written, power cut at each: %d old, %d new\n", total, olds,
	       news);
}

int main(void)
{
	uint8_t seed[32];

	for (int i = 0; i < 32; i++) {
		seed[i] = (uint8_t)i;
	}
	crypto_ed25519_key_pair(secret, public, seed);

	test_herd_change();
	test_power_cut();
	return test_done("herd");
}
