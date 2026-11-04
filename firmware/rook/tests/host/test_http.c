/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_backoff.h"
#include "rook_http.h"
#include "test.h"

int main(void)
{
	struct rook_url u;
	struct rook_http_resp r;
	char head[512];
	char resp_buf[512];
	char *resp = resp_buf;
	size_t off, vl;

	strcpy(resp_buf, "HTTP/1.1 503 Busy\r\nRetry-After: 12\r\nContent-Length: 2\r\n\r\n{}xx");

	CHECK(rook_url_parse("https://farm.example.com/collar/v1/", false, &u) == 0);
	CHECK(u.tls && u.port == 443 && strcmp(u.host, "farm.example.com") == 0 &&
	      strcmp(u.path, "/collar/v1") == 0);
	CHECK(rook_url_parse("http://10.0.0.2:8080/collar/v1", false, &u) == -1);
	CHECK(rook_url_parse("http://10.0.0.2:8080/collar/v1", true, &u) == 0);
	CHECK(!u.tls && u.port == 8080 && strcmp(u.host, "10.0.0.2") == 0);
	CHECK(rook_url_parse("https://:443/x", false, &u) == -1);

	CHECK(rook_url_parse("https://h.example/collar/v1", false, &u) == 0);
	CHECK(rook_http_head(head, sizeof(head), "POST", &u, "/report", "tok", 10) > 0);
	CHECK(strncmp(head, "POST /collar/v1/report HTTP/1.1\r\nHost: h.example\r\n", 50) == 0);
	CHECK(strstr(head, "Content-Length: 10\r\n\r\n") != NULL);

	CHECK(rook_http_parse(resp, strlen(resp), &r) == 0);
	CHECK(r.status == 503 && r.retry_after_s == 12 && r.body_len == 2);
	strcpy(resp_buf, "garbage");
	CHECK(rook_http_parse(resp, 7, &r) == -1);
	strcpy(resp_buf, "HTTP/1.1 204 No Content\r\nDate: Tue, 03 Nov 2026 22:48:05 GMT\r\n\r\n");
	CHECK(rook_http_parse(resp, strlen(resp), &r) == 0 && r.status == 204 && r.body_len == 0);
	CHECK(r.has_date && r.date == 1793746085);

	/* Chunked (a proxy re-chunking), decoded in place */
	strcpy(resp_buf, "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
			 "5\r\n{\"lat\r\nf\r\nest_version\":7}\r\n0\r\n\r\n");
	CHECK(rook_http_parse(resp, strlen(resp), &r) == 0 && r.status == 200);
	CHECK(r.body_len == 20 && memcmp(r.body, "{\"latest_version\":7}", 20) == 0);
	strcpy(resp_buf, "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\nff\r\nshort");
	CHECK(rook_http_parse(resp, strlen(resp), &r) == -1);

	/* Dates */
	CHECK(rook_http_date("Thu, 01 Jan 1970 00:00:00 GMT", 29) == 0);
	CHECK(rook_http_date("Mon, 02 Nov 2026 18:00:00 GMT", 29) == 1793642400);
	CHECK(rook_http_date("Monday, 02-Nov-26 18:00:00 GMT", 30) == -1);

	/* The config in a report response */
	{
		const char *j = "{\"latest_version\":null, \"config\" : {\"a\":{\"b\":\"}\"},\"c\":[1,2]} }";

		CHECK(rook_json_member(j, strlen(j), "config", &off, &vl) == 0);
		CHECK(vl == strlen("{\"a\":{\"b\":\"}\"},\"c\":[1,2]}") &&
		      memcmp(j + off, "{\"a\":{\"b\":\"}\"},\"c\":[1,2]}", vl) == 0);
		CHECK(rook_json_member(j, strlen(j), "latest_version", &off, &vl) == 0 &&
		      vl == 4 && memcmp(j + off, "null", 4) == 0);
		CHECK(rook_json_member(j, strlen(j), "b", &off, &vl) == -1); /* nested only */
		CHECK(rook_json_member("{\"latest_version\":3}", 20, "config", &off, &vl) == -1);
	}

	/* 409 (safety gate) on GET /boundary is "nothing new", not a retry */
	CHECK(rook_boundary_status(409) == 204 && rook_boundary_status(204) == 204 &&
	      rook_boundary_status(503) == 503);
	return test_done("rook http");
}
