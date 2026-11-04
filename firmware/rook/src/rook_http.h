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
	bool has_date;
	int64_t date; /* Date header, Unix s */
	const char *body;
	size_t body_len;
};

/* Parse a whole response in buf (len bytes). A chunked body is decoded in
 * place (Cloudflare and other proxies may re-chunk). -1 if it's not HTTP/1.x
 * or the chunking is broken. */
int rook_http_parse(char *buf, size_t len, struct rook_http_resp *r);

/* An IMF-fixdate ("Tue, 03 Nov 2026 22:48:00 GMT") to Unix s; -1 if not one */
int64_t rook_http_date(const char *s, size_t len);

/* The value of a top-level key of a JSON object (as sent, e.g. the whole
 * nested object). Returns 0 and sets *off and *vlen, or -1 if absent. */
int rook_json_member(const char *json, size_t len, const char *key, size_t *off,
		     size_t *vlen);

#endif
