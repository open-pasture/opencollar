/* SPDX-License-Identifier: Apache-2.0 */
/* Staging endpoint: CA decision, the embedded PEM, URL, Date and the clock guard */
#include <errno.h>
#include <stdio.h>
#include <string.h>

#include "rook_ca.h"
#include "rook_http.h"
#include "rook_report.h"
#include "test.h"

static struct rook_queue q;
static char buf[2048], pem[4096];

int main(void)
{
	/* The Date the staging server sent on 2026-11-04 05:12:20 UTC */
	const char *date = "Wed, 04 Nov 2026 05:12:20 GMT";
	const int64_t now = 1793769140;
	struct rook_url u;
	struct rook_report_info info = {.collar_id = "col_01J9SIMCOLLAR", .fw = "0.2.0"};
	struct rook_sample s = {.lat_e7 = 381240000, .lon_e7 = -924050000, .accuracy_dm = 18,
				.sats = 9, .fence = ROOK_FENCE_INSIDE};
	char raw[] = "HTTP/1.1 204 No Content\r\ndate: Wed, 04 Nov 2026 05:12:20 GMT\r\n"
		     "server: railway-edge\r\n\r\n";
	struct rook_http_resp r;
	uint16_t n, sk;
	FILE *f;
	size_t len;

	CHECK(rook_ca_action(0, false) == ROOK_CA_KEEP);
	CHECK(rook_ca_action(1, true) == ROOK_CA_WRITE);
	CHECK(rook_ca_action(-ENOENT, false) == ROOK_CA_WRITE);
	CHECK(rook_ca_action(-ENOBUFS, true) == ROOK_CA_KEEP);
	CHECK(rook_ca_action(-ENOBUFS, false) == ROOK_CA_WRITE);
	CHECK(rook_ca_action(-EACCES, true) == ROOK_CA_FAIL);

	/* The PEM rook.conf embeds: one certificate, fits the modem's 4 KB credential limit */
	f = fopen("../../certs/isrg-root-x1.pem", "rb");
	CHECK(f != NULL);
	len = f ? fread(pem, 1, sizeof(pem) - 1, f) : 0;
	if (f) {
		fclose(f);
	}
	pem[len] = 0;
	CHECK(len > 1000 && len < 4096);
	CHECK(strncmp(pem, "-----BEGIN CERTIFICATE-----", 27) == 0 &&
	      strstr(pem, "-----END CERTIFICATE-----") &&
	      strstr(pem + 28, "BEGIN") == NULL);

	/* https, default port 443, SNI host = endpoint host, no 7878 */
	CHECK(rook_url_parse("https://op-server-staging-staging.up.railway.app/collar/v1", false,
			     &u) == 0);
	CHECK(u.tls && u.port == 443 &&
	      strcmp(u.host, "op-server-staging-staging.up.railway.app") == 0 &&
	      strcmp(u.path, "/collar/v1") == 0);
	CHECK(rook_http_head(buf, sizeof(buf), "GET", &u, "/boundary?have=0", "k", 0) > 0 &&
	      strstr(buf, "GET /collar/v1/boundary?have=0 HTTP/1.1\r\n") &&
	      strstr(buf, "\r\nHost: op-server-staging-staging.up.railway.app\r\n"));
	CHECK(rook_url_parse("http://op-server-staging-staging.up.railway.app/collar/v1", false,
			     &u) == -1);
	/* The mock config still parses (http allowed only there) */
	CHECK(rook_url_parse("http://203.0.113.10:7878/collar/v1", true, &u) == 0 && !u.tls &&
	      u.port == 7878);

	/* Date: the header as sent (lower-case name over HTTP/2-style edges) */
	CHECK(rook_http_date(date, strlen(date)) == now);
	CHECK(rook_http_parse(raw, strlen(raw), &r) == 0 && r.status == 204 && r.has_date &&
	      r.date == now);

	/* The 9-minute guard against that clock */
	rook_queue_init(&q);
	s.at = now - 30;
	rook_queue_push(&q, &s);
	s.at = now + 540;
	rook_queue_push(&q, &s); /* exactly 9 min: sent */
	s.at = now + 541;
	rook_queue_push(&q, &s); /* left out */
	info.has_server_now = true;
	info.server_now = now;
	CHECK(rook_report_encode(&info, &q, 10, buf, sizeof(buf), &n, &sk) > 0 && n == 3 &&
	      sk == 1);
	CHECK(strstr(buf, "2026-11-04T05:11:50Z") && strstr(buf, "2026-11-04T05:21:20Z") &&
	      !strstr(buf, "05:21:21Z"));
	if (failures) {
		printf("%s\n", buf);
	}
	return test_done("rook ca/staging");
}
