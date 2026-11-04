/* SPDX-License-Identifier: Apache-2.0 */
/* The core's state as the report and boundary query carry it */
#include <stdio.h>

#include "rook_fence.h"
#include "rook_http.h"
#include "rook_report.h"
#include "rook_state.h"
#include "store_ram.h"
#include "test.h"

static struct app a;
static char reply[256], wire[4096], buf[3072];
static const struct cue_config cue_cfg = {0};
static const struct geofence_config gdef = {.warn_m = 5, .hysteresis_m = 1};

int main(void)
{
	/* The spec's provisioning line: 64-hex key, e ending in /collar/v1 */
	const char *prov =
		"provision {\"v\":1,\"c\":\"col_01J9SIMCOLLAR\",\"h\":\"herd_01J7GOLDEN\","
		"\"k\":\"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\","
		"\"e\":\"https://rook.example.net/collar/v1\","
		"\"s\":\"A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg=\"}";
	struct rook_dev_state d;
	struct rook_report_info info = {.collar_id = "col_01J9SIMCOLLAR", .fw = APP_FW_VERSION};
	struct rook_queue q;
	struct rook_url u;
	uint16_t n, sk;
	char qs[80];
	FILE *f;
	size_t len;

	store_ram_reset();
	app_init(&a, &cue_cfg, &gdef);
	app_boot(&a, 0);
	rook_state_take(&a, &d);
	CHECK(!d.provisioned && d.n_slots == 0);

	app_line(&a, prov, strlen(prov), false, 0, reply, sizeof(reply));
	CHECK(strcmp(reply, "ok col_01J9SIMCOLLAR") == 0);
	rook_state_take(&a, &d);
	CHECK(d.provisioned && strcmp(d.endpoint, "https://rook.example.net/collar/v1") == 0);
	CHECK(rook_url_parse(d.endpoint, false, &u) == 0 && u.tls && u.port == 443 &&
	      strcmp(u.path, "/collar/v1") == 0);
	CHECK(strlen(a.prov.key) == 64);
	CHECK(d.report_s == 60 && !d.has_config && d.have == 0 && d.free == d.limits.slots);

	f = fopen(SAMPLES "/boundary_v1.json", "rb");
	CHECK(f != NULL);
	len = fread(wire, 1, sizeof(wire) - 1, f);
	fclose(f);
	while (len && (wire[len - 1] == '\n' || wire[len - 1] == '\r')) {
		len--;
	}
	rook_fence_reset();
	CHECK(rook_fence_download(&a, wire, len, 1000).code == REJECT_NONE);
	rook_state_take(&a, &d);
	CHECK(d.n_slots == 1 && d.slot[0].version == 1 && d.slot[0].applied);
	CHECK(d.have == 1 && d.free == d.limits.slots - 1u && d.has_free_bytes &&
	      d.free_bytes < d.limits.slot_bytes);

	rook_queue_init(&q);
	info.dev = &d;
	CHECK(rook_report_encode(&info, &q, 0, buf, sizeof(buf), &n, &sk) > 0);
	CHECK(strstr(buf, "\"slots\":[{\"version\":1,\"status\":\"applied\"}]") != NULL);
	CHECK(strstr(buf, "\"limits\":{\"outer\":") != NULL && !strstr(buf, "config_version"));
	CHECK(rook_boundary_query(1, &d, qs, sizeof(qs)) > 0 &&
	      strncmp(qs, "/boundary?have=1&free=", 22) == 0 && strstr(qs, "&free_bytes="));
	if (failures) {
		printf("%s\n%s\n", buf, qs);
	}

	/* A config in the report reply (mock-signed), applied by the core */
	{
		size_t off, vl;

		f = fopen(SAMPLES "/report_response_config.json", "rb");
		CHECK(f != NULL);
		len = fread(wire, 1, sizeof(wire) - 1, f);
		fclose(f);
		CHECK(rook_json_member(wire, len, "config", &off, &vl) == 0 && wire[off] == '{');
		CHECK(app_config(&a, wire + off, vl, 2000) == REJECT_NONE);
		rook_state_take(&a, &d);
		CHECK(d.has_config && d.config_version == 3 && d.report_s == 30);
		CHECK(rook_report_encode(&info, &q, 0, buf, sizeof(buf), &n, &sk) > 0 &&
		      strstr(buf, "\"config_version\":3"));
		/* The same again: stale, kept to report once as config_reject */
		CHECK(app_config(&a, wire + off, vl, 3000) == REJECT_STALE);
		rook_state_take(&a, &d);
		CHECK(d.has_config_reject && d.config_reject_version == 3);
		CHECK(rook_report_encode(&info, &q, 0, buf, sizeof(buf), &n, &sk) > 0 &&
		      strstr(buf, "\"config_reject\":{\"version\":3,\"code\":\"stale\"}"));
	}
	return test_done("rook state");
}
