/*
 * Report telemetry encoders: last_cue_at, hdop on fixes, rsrp_dbm setter,
 * battery omitted when unknown (never reported as 0 for unknown).
 * Cases also live in protocol/vectors/report.json (byte-identical copy here).
 */
#include "../../src/app.h"
#include "../../src/report.h"
#include "json.h"
#include "store_ram.h"
#include "test.h"
#include "v0_fixtures.h"

#define T_CUE 1790510520 /* 2026-09-27T12:02:00Z */

static struct jval *vecs;

static void load_vecs(void)
{
	vecs = json_load(VECTORS "/report.json");
	CHECK(vecs != NULL);
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

static void expect_wire(const char *case_name, const char *got)
{
	const struct jval *k = case_named(case_name);
	const char *want = jstr(k, "wire");

	CHECK_CASE(strcmp(got, want) == 0, case_name, "got [%s] want [%s]", got, want);
}

static void test_battery_omit_unknown(void)
{
	char buf[64];
	int n;

	report_clear_signal_dbm();
	report_clear_last_cue_at();

	n = report_encode_battery(false, 0.0, buf, sizeof(buf));
	CHECK(n == 0);
	CHECK(buf[0] == '\0');
	/* Unknown must never become a literal battery:0 on the wire */
	CHECK(strstr(buf, "battery") == NULL);
	expect_wire("battery_unknown_omitted", "");

	n = report_encode_battery(true, 0.81, buf, sizeof(buf));
	CHECK(n > 0);
	expect_wire("battery_known", buf);

	/* A measured empty pack may encode 0; that is known, not unknown */
	n = report_encode_battery(true, 0.0, buf, sizeof(buf));
	CHECK(n > 0);
	expect_wire("battery_known_zero", buf);
}

static void test_fix_hdop(void)
{
	struct report_fix f = {
		.at = T_CUE,
		.lon = -92.405,
		.lat = 38.124,
		.accuracy_m = 1.8,
		.has_sats = true,
		.sats = 9,
		.has_cn0 = true,
		.cn0 = 41.0,
		.has_hdop = true,
		.hdop = 0.9,
	};
	char buf[256];
	int n;

	n = report_encode_fix(&f, buf, sizeof(buf));
	CHECK(n > 0);
	expect_wire("fix_with_hdop", buf);
	CHECK(strstr(buf, "\"accuracy_m\":1.8") != NULL);
	CHECK(strstr(buf, "\"hdop\":0.9") != NULL);

	f.has_hdop = false;
	n = report_encode_fix(&f, buf, sizeof(buf));
	CHECK(n > 0);
	expect_wire("fix_without_hdop", buf);
	CHECK(strstr(buf, "hdop") == NULL);
	CHECK(strstr(buf, "\"accuracy_m\":1.8") != NULL);
}

static void test_health_telemetry(void)
{
	char buf[128];
	int n;
	int64_t got_t;
	int got_rsrp;

	report_clear_last_cue_at();
	report_clear_signal_dbm();

	n = report_encode_health_telemetry(buf, sizeof(buf));
	CHECK(n == 2 && strcmp(buf, "{}") == 0);
	expect_wire("health_empty", buf);
	CHECK(!report_get_last_cue_at(NULL));
	CHECK(!report_get_signal_dbm(NULL));

	report_note_cue_at(T_CUE);
	CHECK(report_get_last_cue_at(&got_t) && got_t == T_CUE);
	n = report_encode_health_telemetry(buf, sizeof(buf));
	CHECK(n > 0);
	expect_wire("health_last_cue_at", buf);

	report_set_signal_dbm(-104);
	CHECK(report_get_signal_dbm(&got_rsrp) && got_rsrp == -104);
	n = report_encode_health_telemetry(buf, sizeof(buf));
	CHECK(n > 0);
	expect_wire("health_last_cue_and_rsrp", buf);
	CHECK(strstr(buf, "\"rssi_dbm\"") == NULL);

	report_clear_last_cue_at();
	n = report_encode_health_telemetry(buf, sizeof(buf));
	CHECK(n > 0);
	expect_wire("health_rsrp_only", buf);

	report_clear_signal_dbm();
	n = report_encode_health_telemetry(buf, sizeof(buf));
	CHECK(strcmp(buf, "{}") == 0);
}

static void test_last_cue_from_app_fix(void)
{
	struct app a;
	struct geofence_config gcfg = CFG;
	struct app_fix_out out;
	struct geo_point sq[] = {at(0, 0), at(100, 0), at(100, 100), at(0, 100)};
	struct geo_point inside = at(50, 50);
	struct geo_point warn = at(50, 2); /* within warn_m of the south edge */
	char buf[128];
	int64_t ms = 1000;

	report_clear_last_cue_at();
	store_ram_reset();
	app_init(&a, &CUE_CFG, &gcfg);
	app_boot(&a, ms);
	CHECK(app_bench(&a, sq, 4, ms));

	out = app_fix(&a,
		       &(struct app_fix_in){.valid = true,
					   .lat = inside.lat,
					   .lon = inside.lon,
					   .accuracy_m = 2,
					   .has_time = true,
					   .utc = T_CUE - 60},
		       ms += 1000);
	CHECK(out.fenced && out.r.state == GEOFENCE_INSIDE);
	CHECK(!out.cmd.active);
	CHECK(!report_get_last_cue_at(NULL));

	out = app_fix(&a,
		       &(struct app_fix_in){.valid = true,
					   .lat = warn.lat,
					   .lon = warn.lon,
					   .accuracy_m = 2,
					   .has_time = true,
					   .utc = T_CUE},
		       ms += 1000);
	CHECK(out.cmd.active && out.cmd.kind == CUE_WARN);
	CHECK(report_get_last_cue_at(NULL));
	CHECK(report_encode_health_telemetry(buf, sizeof(buf)) > 0);
	CHECK(strstr(buf, "\"last_cue_at\":\"2026-09-27T12:02:00Z\"") != NULL);
}

int main(void)
{
	load_vecs();
	test_battery_omit_unknown();
	test_fix_hdop();
	test_health_telemetry();
	test_last_cue_from_app_fix();
	return test_done("report telemetry");
}
