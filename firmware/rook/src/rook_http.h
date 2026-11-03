/* SPDX-License-Identifier: Apache-2.0 */
/* Tiny HTTP/1.1 helpers for the reporter: URL split, request head, response
 * parse. One request per connection (Connection: close). Host-testable. */
#ifndef ROOK_HTTP_H
#define ROOK_HTTP_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

struct rook_url {
	bool tls;
	char host[128];
	uint16_t port;
	char path[160]; /* Prefix without trailing '/', e.g. "/collar/v1" */
};

/* https://host[:port][/path]; http:// only when allow_http (mock server) */
int rook_url_parse(const char *url, bool allow_http, struct rook_url *u);

/* Request head into out; returns length or -1 */
int rook_http_head(char *out, size_t cap, const char *method, const struct rook_url *u,
		   const char *suffix, const char *token, size_t body_len);

struct rook_http_resp {
	int status;
	int32_t retry_after_s; /* -1 none */
	const char *body;
	size_t body_len;
};

/* Parse a whole response in buf (len bytes). -1 if it's not HTTP/1.x */
int rook_http_parse(const char *buf, size_t len, struct rook_http_resp *r);

#endif
