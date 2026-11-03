/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_http.h"
#include "test.h"

int main(void)
{
	struct rook_url u;
	struct rook_http_resp r;
	char head[512];
	const char *resp = "HTTP/1.1 503 Busy\r\nRetry-After: 12\r\nContent-Length: 2\r\n\r\n{}xx";

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
	CHECK(rook_http_parse("garbage", 7, &r) == -1);
	resp = "HTTP/1.1 204 No Content\r\n\r\n";
	CHECK(rook_http_parse(resp, strlen(resp), &r) == 0 && r.status == 204 && r.body_len == 0);
	return test_done("rook http");
}
