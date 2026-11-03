/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_report.h"
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
	uint16_t n;
	int len;

	rook_queue_init(&q);
	rook_queue_push(&q, &s);
	s.fence = ROOK_FENCE_OUTSIDE;
	s.margin_cm = -5;
	s.lat_e7 = -1;
	rook_queue_push(&q, &s);
	len = rook_report_encode(&info, &q, 10, buf, sizeof(buf), &n);
	CHECK(n == 2);
	CHECK(len == (int)strlen(buf));
	CHECK(strcmp(buf,
		     "{\"boundary_version\":57,\"collar_id\":\"col_1\",\"device\":{\"fw\":\"0.2.0\","
		     "\"caps\":[\"holes\",\"slots\",\"collar_id\",\"cue_mode\"]},\"fixes\":["
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
	len = rook_report_encode(&info, &q, 10, buf, 400, &n);
	CHECK(len > 0 && n == 1 && buf[len - 1] == '}');
	len = rook_report_encode(&info, &q, 10, buf, 60, &n);
	CHECK(len == -1);

	/* No battery: omitted */
	info.has_battery = false;
	info.has_charging = false;
	len = rook_report_encode(&info, &q, 0, buf, sizeof(buf), &n);
	CHECK(n == 0 && strstr(buf, "battery") == NULL && strstr(buf, "\"fixes\":[]") != NULL);
	return test_done("rook report");
}
