/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_report.h"
#include "slots.h"
#include "test.h"

static struct rook_queue q;
static char buf[2048];

int main(void)
{
	struct rook_report_info info = {
		.collar_id = "col_1", .fw = "0.2.0", .boundary_version = 57,
		.has_battery = true, .soc = 0.81f, .battery_v = 3.31f,
		.has_charging = true, .charging = true, .uptime_s = 86400,
	};
	struct rook_sample s = {
		.at = 1793642400, /* 2026-11-02T18:00:00Z */
		.lat_e7 = 381240000, .lon_e7 = -924050000, .accuracy_dm = 18, .sats = 9,
		.fence = ROOK_FENCE_INSIDE, .margin_cm = 1234, .boundary_version = 57,
	};
	uint16_t n, sk;
	int len;

	rook_queue_init(&q);
	rook_queue_push(&q, &s);
	s.fence = ROOK_FENCE_OUTSIDE;
	s.margin_cm = -5;
	s.lat_e7 = -1;
	rook_queue_push(&q, &s);
	len = rook_report_encode(&info, &q, 10, buf, sizeof(buf), &n, &sk);
	CHECK(n == 2);
	CHECK(len == (int)strlen(buf));
	CHECK(strcmp(buf,
		     "{\"boundary_version\":57,\"collar_id\":\"col_1\",\"device\":{\"fw\":\"0.2.0\","
		     "\"caps\":[\"holes\",\"slots\",\"collar_id\",\"cue_mode\",\"config\"]},\"fixes\":["
		     "{\"at\":\"2026-11-02T18:00:00Z\",\"point\":[-92.405,38.124],\"accuracy_m\":1.8,"
		     "\"sats\":9,\"fence\":\"inside\",\"margin_m\":12.34},"
		     "{\"at\":\"2026-11-02T18:00:00Z\",\"point\":[-92.405,-0.0000001],\"accuracy_m\":1.8,"
		     "\"sats\":9,\"fence\":\"outside\",\"margin_m\":-0.05}],"
		     "\"battery\":0.81,\"health\":{\"battery_v\":3.31,\"charging\":true,"
		     "\"uptime_s\":86400,\"dropped\":0}}") == 0);
	if (failures) {
		printf("%s\n", buf);
	}

	/* A small buffer takes fewer fixes, never a broken body */
	len = rook_report_encode(&info, &q, 10, buf, 400, &n, &sk);
	CHECK(len > 0 && n == 1 && buf[len - 1] == '}');
	len = rook_report_encode(&info, &q, 10, buf, 60, &n, &sk);
	CHECK(len == -1);

	/* No battery: omitted */
	info.has_battery = false;
	info.has_charging = false;
	len = rook_report_encode(&info, &q, 0, buf, sizeof(buf), &n, &sk);
	CHECK(n == 0 && strstr(buf, "battery") == NULL && strstr(buf, "\"fixes\":[]") != NULL);
	CHECK(sk == 0);

	/* Device limits, config and slots */
	{
		struct rook_dev_state d = {
			.provisioned = true,
			.limits = {128, 16, 32, 384, 16, 24576},
			.n_slots = 2,
			.slot = {{.version = 57, .applied = true},
				 {.version = 58, .has_effective_at = true, .effective_at = 1793642400}},
			.has_config = true, .config_version = 3,
			.has_config_reject = true, .config_reject_version = 4,
			.config_reject_code = REJECT_STALE,
			.have = 58, .free = 14, .has_free_bytes = true, .free_bytes = 20000,
		};
		char qs[80];

		info.dev = &d;
		len = rook_report_encode(&info, &q, 0, buf, sizeof(buf), &n, &sk);
		CHECK(len > 0);
		CHECK(strstr(buf, "\"device\":{\"fw\":\"0.2.0\",\"caps\":[\"holes\",\"slots\","
			     "\"collar_id\",\"cue_mode\",\"config\"],\"limits\":{\"outer\":128,"
			     "\"holes\":16,\"hole_vertices\":32,\"total\":384,\"slots\":16,"
			     "\"slot_bytes\":24576},\"config_version\":3,\"config_reject\":"
			     "{\"version\":4,\"code\":\"stale\"}},\"slots\":[{\"version\":57,"
			     "\"status\":\"applied\"},{\"version\":58,\"status\":\"received\","
			     "\"effective_at\":\"2026-11-02T18:00:00Z\"}],\"fixes\":[]") != NULL);
		if (failures) {
			printf("%s\n", buf);
		}
		CHECK(rook_boundary_query(58, &d, qs, sizeof(qs)) > 0 &&
		      strcmp(qs, "/boundary?have=58&free=14&free_bytes=20000") == 0);
		d.has_free_bytes = false;
		CHECK(rook_boundary_query(58, &d, qs, sizeof(qs)) > 0 &&
		      strcmp(qs, "/boundary?have=58&free=14") == 0);
		CHECK(rook_boundary_query(7, NULL, qs, sizeof(qs)) > 0 &&
		      strcmp(qs, "/boundary?have=7") == 0);
		info.dev = NULL;
	}

	/* Clock: fixes more than 9 min ahead of the server, or before 2024, are
	 * left out (counted, consumed), never sent to earn a 400 */
	rook_queue_init(&q);
	s.at = 1793642400;
	rook_queue_push(&q, &s);           /* fine */
	s.at = 1793642400 + 600;
	rook_queue_push(&q, &s);           /* 10 min ahead of the server */
	s.at = 315964800;
	rook_queue_push(&q, &s);           /* 1980: GNSS time not set */
	s.at = 1793642400 + 500;
	rook_queue_push(&q, &s);           /* within 9 min */
	info.has_server_now = true;
	info.server_now = 1793642400;
	len = rook_report_encode(&info, &q, 10, buf, sizeof(buf), &n, &sk);
	CHECK(len > 0 && n == 4 && sk == 2);
	CHECK(strstr(buf, "18:00:00Z") && strstr(buf, "18:08:20Z") && !strstr(buf, "18:10:00Z") &&
	      !strstr(buf, "1980"));
	/* Unknown server time: only the pre-2024 one goes */
	info.has_server_now = false;
	len = rook_report_encode(&info, &q, 10, buf, sizeof(buf), &n, &sk);
	CHECK(len > 0 && n == 4 && sk == 1);

	/* Ack: at always present (the server requires it) */
	{
		struct slot_ack ack = {.version = 2, .status = ACK_REJECTED, .code = REJECT_BAD_SIG};

		strcpy(ack.command_id.s, "bnd_2");
		len = rook_ack_encode(&ack, false, 0, buf, sizeof(buf));
		CHECK(len > 0 && strcmp(buf, "{\"command_id\":\"bnd_2\",\"version\":2,\"status\":"
					     "\"rejected\",\"code\":\"bad_sig\",\"at\":"
					     "\"1970-01-01T00:00:00Z\"}") == 0);
		len = rook_ack_encode(&ack, true, 1793642400, buf, sizeof(buf));
		CHECK(len > 0 && strstr(buf, "\"at\":\"2026-11-02T18:00:00Z\"}"));
		ack.status = ACK_APPLIED;
		ack.has_at = true;
		ack.at = 1793642401;
		len = rook_ack_encode(&ack, true, 1793642400, buf, sizeof(buf));
		CHECK(len > 0 && strcmp(buf, "{\"command_id\":\"bnd_2\",\"version\":2,\"status\":"
					     "\"applied\",\"at\":\"2026-11-02T18:00:01Z\"}") == 0);
		if (failures) {
			printf("%s\n", buf);
		}
	}
	return test_done("rook report");
}
