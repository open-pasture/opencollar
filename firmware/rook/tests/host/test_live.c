/* SPDX-License-Identifier: Apache-2.0 */
/* The Rook's own encoders against the running mock server (run.sh starts it):
 * report, boundary query and ack over plain HTTP with the bearer key. */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#include "rook_backoff.h"
#include "rook_http.h"
#include "rook_report.h"
#include "slots.h"
#include "test.h"

static char rx[16384], head[512], body[3072];
static struct rook_url u;
static const char *key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

static int xfer(const char *method, const char *suffix, const char *tok, const char *b,
		size_t bl, struct rook_http_resp *r)
{
	struct sockaddr_in sa = {.sin_family = AF_INET, .sin_port = htons(u.port)};
	int fd = socket(AF_INET, SOCK_STREAM, 0), total = 0, n;
	int hl = rook_http_head(head, sizeof(head), method, &u, suffix, tok, bl);

	inet_pton(AF_INET, u.host, &sa.sin_addr);
	if (fd < 0 || hl < 0 || connect(fd, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
		return -1;
	}
	if (write(fd, head, hl) != hl || (bl && write(fd, b, bl) != (ssize_t)bl)) {
		close(fd);
		return -1;
	}
	while ((n = read(fd, rx + total, sizeof(rx) - 1 - total)) > 0) {
		total += n;
	}
	close(fd);
	rx[total] = 0;
	return rook_http_parse(rx, total, r) == 0 ? r->status : -1;
}

int main(int argc, char **argv)
{
	struct rook_http_resp r;
	struct rook_queue q;
	struct rook_dev_state d = {.provisioned = true, .limits = {128, 16, 32, 384, 16, 24576},
				   .n_slots = 1, .slot = {{.version = 1, .applied = true}},
				   .have = 1, .free = 15, .has_free_bytes = true,
				   .free_bytes = 24000};
	struct rook_report_info info = {.collar_id = "col_01J9SIMCOLLAR", .fw = "0.2.0",
					.boundary_version = 1, .dev = &d, .uptime_s = 5};
	struct rook_sample s = {.lat_e7 = 381240000, .lon_e7 = -924050000, .accuracy_dm = 18,
				.sats = 9, .fence = ROOK_FENCE_INSIDE, .margin_cm = 1234};
	struct slot_ack ack = {.version = 2, .status = ACK_APPLIED};
	char qs[80];
	uint16_t n, sk;
	int len;

	if (argc < 2 || rook_url_parse(argv[1], true, &u) != 0) {
		printf("usage: test_live http://127.0.0.1:PORT/collar/v1\n");
		return 2;
	}
	CHECK(xfer("GET", "/boundary?have=0", "nope", NULL, 0, &r) == 401);
	CHECK(r.has_date && llabs(r.date - (int64_t)time(NULL)) < 5);

	/* A position with battery: the shortest path to the app */
	rook_queue_init(&q);
	s.at = time(NULL) - 20;
	rook_queue_push(&q, &s);
	s.at = time(NULL) + 20 * 60; /* a bad clock: left out, not a 400 */
	rook_queue_push(&q, &s);
	info.has_battery = true;
	info.soc = 0.81f;
	info.battery_v = 3.9f;
	info.has_server_now = true;
	info.server_now = r.date;
	len = rook_report_encode(&info, &q, 12, body, sizeof(body), &n, &sk);
	CHECK(len > 0 && n == 2 && sk == 1);
	CHECK(xfer("POST", "/report", key, body, len, &r) == 200);
	CHECK(r.body_len && strstr(r.body, "\"latest_version\":1"));
	if (failures) {
		printf("%s\n%s\n", body, rx);
	}
	/* Without the clock guard the server refuses the whole batch */
	info.has_server_now = false;
	q.head = 1, q.n = 1;
	len = rook_report_encode(&info, &q, 12, body, sizeof(body), &n, &sk);
	CHECK(xfer("POST", "/report", key, body, len, &r) == 400);
	CHECK(rook_http_action(400, 0) == ROOK_ACT_DROP);

	/* Wrong collar id for the key */
	info.collar_id = "col_other";
	len = rook_report_encode(&info, &q, 0, body, sizeof(body), &n, &sk);
	CHECK(xfer("POST", "/report", key, body, len, &r) == 403);

	CHECK(rook_boundary_query(0, &d, qs, sizeof(qs)) > 0);
	CHECK(xfer("GET", qs, key, NULL, 0, &r) == 200 && r.body_len > 100);
	CHECK(rook_boundary_query(1, &d, qs, sizeof(qs)) > 0);
	CHECK(rook_boundary_status(xfer("GET", qs, key, NULL, 0, &r)) == 204);

	strcpy(ack.command_id.s, "bnd_rook_1");
	len = rook_ack_encode(&ack, false, 0, body, sizeof(body)); /* no time at all */
	CHECK(xfer("POST", "/ack", key, body, len, &r) == 204);
	return test_done("rook live (mock server)");
}
