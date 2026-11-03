/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_http.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

int rook_url_parse(const char *url, bool allow_http, struct rook_url *u)
{
	const char *p, *host_end, *slash;
	size_t hl;

	memset(u, 0, sizeof(*u));
	if (strncmp(url, "https://", 8) == 0) {
		u->tls = true;
		u->port = 443;
		p = url + 8;
	} else if (allow_http && strncmp(url, "http://", 7) == 0) {
		u->port = 80;
		p = url + 7;
	} else {
		return -1;
	}
	slash = strchr(p, '/');
	host_end = slash ? slash : p + strlen(p);
	for (const char *c = p; c < host_end; c++) {
		if (*c == ':') {
			long port = strtol(c + 1, NULL, 10);

			if (port <= 0 || port > 65535) {
				return -1;
			}
			u->port = (uint16_t)port;
			host_end = c;
			break;
		}
	}
	hl = (size_t)(host_end - p);
	if (hl == 0 || hl >= sizeof(u->host)) {
		return -1;
	}
	memcpy(u->host, p, hl);
	if (slash) {
		size_t pl = strlen(slash);

		while (pl > 0 && slash[pl - 1] == '/') {
			pl--;
		}
		if (pl >= sizeof(u->path)) {
			return -1;
		}
		memcpy(u->path, slash, pl);
	}
	return 0;
}

int rook_http_head(char *out, size_t cap, const char *method, const struct rook_url *u,
		   const char *suffix, const char *token, size_t body_len)
{
	int k = snprintf(out, cap,
			 "%s %s%s HTTP/1.1\r\nHost: %s\r\nAuthorization: Bearer %s\r\n"
			 "Connection: close\r\n",
			 method, u->path, suffix, u->host, token);
	int k2;

	if (k < 0 || (size_t)k >= cap) {
		return -1;
	}
	if (body_len) {
		k2 = snprintf(out + k, cap - k,
			      "Content-Type: application/json\r\nContent-Length: %u\r\n\r\n",
			      (unsigned)body_len);
	} else {
		k2 = snprintf(out + k, cap - k, "\r\n");
	}
	if (k2 < 0 || (size_t)k2 >= cap - k) {
		return -1;
	}
	return k + k2;
}

int rook_http_parse(const char *buf, size_t len, struct rook_http_resp *r)
{
	const char *end = buf + len, *line, *eol;
	long clen = -1;

	memset(r, 0, sizeof(*r));
	r->retry_after_s = -1;
	if (len < 12 || strncmp(buf, "HTTP/1.", 7) != 0) {
		return -1;
	}
	r->status = atoi(buf + 9);
	line = memchr(buf, '\n', len);
	while (line && ++line < end) {
		eol = memchr(line, '\n', (size_t)(end - line));
		if (!eol) {
			return -1;
		}
		if (eol - line <= 1) { /* blank line */
			r->body = eol + 1;
			r->body_len = (size_t)(end - r->body);
			if (clen >= 0 && (size_t)clen < r->body_len) {
				r->body_len = (size_t)clen;
			}
			return 0;
		}
		if (strncasecmp(line, "Retry-After:", 12) == 0) {
			r->retry_after_s = (int32_t)atol(line + 12);
		} else if (strncasecmp(line, "Content-Length:", 15) == 0) {
			clen = atol(line + 15);
		}
		line = eol;
	}
	return -1;
}
