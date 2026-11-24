/* SPDX-License-Identifier: Apache-2.0 */
/* Pending acks: kept in NVS across reboots, resent with their `at`, dropped on 204/4xx */
#include <stdio.h>

#include "rook_fence.h"
#include "rook_report.h"
#include "rook_state.h"
#include "store_ram.h"
#include "test.h"

static struct app a;
static char reply[256], wire[4096], buf[512];
static const struct cue_config cue_cfg = {0};
static const struct geofence_config gdef = {.warn_m = 5, .hysteresis_m = 1};

static void reboot(void)
{
	store_ram_reboot();
	memset(&a, 0, sizeof(a));
	app_init(&a, &cue_cfg, &gdef);
	app_boot(&a, 0);
}

int main(void)
{
	const char *prov =
		"provision {\"v\":1,\"c\":\"col_01J9SIMCOLLAR\",\"h\":\"herd_01J7GOLDEN\","
		"\"k\":\"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\","
		"\"e\":\"https://rook.example.net/collar/v1\","
		"\"s\":\"A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg=\"}";
	struct rook_dev_state d;
	struct slot_ack sent, timed = {.version = 7, .status = ACK_REJECTED,
				       .code = REJECT_STALE, .has_at = true, .at = 1790000000};
	FILE *f;
	size_t len;

	CHECK(rook_ack_fate(204) == ROOK_ACK_DONE && rook_ack_fate(200) == ROOK_ACK_DONE);
	CHECK(rook_ack_fate(400) == ROOK_ACK_DROP && rook_ack_fate(403) == ROOK_ACK_DROP &&
	      rook_ack_fate(404) == ROOK_ACK_DROP && rook_ack_fate(409) == ROOK_ACK_DROP);
	CHECK(rook_ack_fate(401) == ROOK_ACK_KEEP && rook_ack_fate(429) == ROOK_ACK_KEEP &&
	      rook_ack_fate(503) == ROOK_ACK_KEEP && rook_ack_fate(-110) == ROOK_ACK_KEEP);

	store_ram_reset();
	app_init(&a, &cue_cfg, &gdef);
	app_boot(&a, 0);
	app_line(&a, prov, strlen(prov), false, 0, reply, sizeof(reply));
	CHECK(strcmp(reply, "ok col_01J9SIMCOLLAR") == 0);
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
	CHECK(d.has_ack && d.ack.version == 1 && d.acks_waiting == 1);

	/* Power goes before the POST: the ack is still there after the reboot */
	reboot();
	rook_state_take(&a, &d);
	CHECK(d.has_ack && d.ack.version == 1 && d.ack.status == ACK_APPLIED);
	sent = d.ack;
	/* No clock when it was made: `at` is the server's Date at send time */
	CHECK(rook_ack_encode(&sent, true, 1790000123, buf, sizeof(buf)) > 0 &&
	      strstr(buf, "\"at\":") && strstr(buf, "\"version\":1"));
	if (failures) {
		printf("%s\n", buf);
	}
	/* Network error, 401, 503: kept, and still there after another reboot */
	CHECK(!rook_acks_settle(&a, &sent, -110));
	CHECK(!rook_acks_settle(&a, &sent, 401));
	CHECK(!rook_acks_settle(&a, &sent, 503));
	reboot();
	rook_state_take(&a, &d);
	CHECK(d.has_ack && d.ack.version == 1);
	/* A different ack never pops the head */
	CHECK(!rook_acks_settle(&a, &timed, 204));
	/* 204: gone, for good */
	CHECK(rook_acks_settle(&a, &sent, 204));
	rook_state_take(&a, &d);
	CHECK(!d.has_ack);
	reboot();
	rook_state_take(&a, &d);
	CHECK(!d.has_ack);

	/* An ack made with a clock keeps its own `at` across a reboot */
	CHECK(proto_id_set(&timed.command_id, "cmd_01J9STALE", 13));
	CHECK(acks_push(&a.acks, &timed) == 0);
	reboot();
	rook_state_take(&a, &d);
	CHECK(d.has_ack && d.ack.has_at && d.ack.at == 1790000000);
	CHECK(rook_ack_encode(&d.ack, true, 1790009999, buf, sizeof(buf)) > 0 &&
	      !strstr(buf, "1790009999"));
	/* 4xx: the server will never take it; dropped, survives no reboot */
	CHECK(rook_acks_settle(&a, &d.ack, 400));
	reboot();
	rook_state_take(&a, &d);
	CHECK(!d.has_ack);
	return test_done("rook acks");
}
