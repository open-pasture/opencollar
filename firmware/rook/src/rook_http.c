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

static int64_t days_from_civil(int y, unsigned m, unsigned d)
{
	/* Howard Hinnant's public-domain algorithm */
	y -= m <= 2;
	const int era = (y >= 0 ? y : y - 399) / 400;
	const unsigned yoe = (unsigned)(y - era * 400);
	const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
	const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;

	return (int64_t)era * 146097 + (int64_t)doe - 719468;
}

int64_t rook_http_date(const char *s, size_t len)
{
	static const char months[] = "JanFebMarAprMayJunJulAugSepOctNovDec";
	char b[40];
	char mon[4];
	int d, y, hh, mm, ss, k = 0;
	const char *m;

	while (len && (*s == ' ' || *s == '\t')) {
		s++, len--;
	}
	if (len >= sizeof(b)) {
		return -1;
	}
	memcpy(b, s, len);
	b[len] = 0;
	if (sscanf(b, "%*3s, %2d %3s %4d %2d:%2d:%2d GMT%n", &d, mon, &y, &hh, &mm, &ss, &k) !=
		    6 ||
	    k == 0) {
		return -1;
	}
	m = strstr(months, mon);
	if (!m || (m - months) % 3 || d < 1 || d > 31 || hh > 23 || mm > 59 || ss > 60) {
		return -1;
	}
	return days_from_civil(y, (unsigned)((m - months) / 3 + 1), (unsigned)d) * 86400 +
	       hh * 3600 + mm * 60 + ss;
}

/* Decode a chunked body in place; returns its length or -1 */
static long dechunk(char *b, size_t len)
{
	size_t in = 0, out = 0;

	for (;;) {
		char *e;
		unsigned long n;
		const char *eol = memchr(b + in, '\n', len - in);

		if (!eol) {
			return -1;
		}
		n = strtoul(b + in, &e, 16);
		if (e == b + in) {
			return -1;
		}
		in = (size_t)(eol - b) + 1;
		if (n == 0) {
			return (long)out;
		}
		if (n > len - in) {
			return -1;
		}
		memmove(b + out, b + in, n);
		out += n;
		in += n;
		if (in < len && b[in] == '\r') {
			in++;
		}
		if (in < len && b[in] == '\n') {
			in++;
		}
		if (in >= len) {
			return -1;
		}
	}
}

int rook_json_member(const char *j, size_t len, const char *key, size_t *off, size_t *vlen)
{
	size_t kl = strlen(key), i = 0;
	int depth = 0;

	while (i < len && j[i] != '{') {
		i++;
	}
	for (; i < len; i++) {
		char c = j[i];

		if (c == '"') {
			size_t start = ++i;

			while (i < len && j[i] != '"') {
				i += j[i] == '\\' ? 2 : 1;
			}
			if (i >= len) {
				return -1;
			}
			if (depth == 1 && i - start == kl && memcmp(j + start, key, kl) == 0) {
				size_t v = i + 1, e;
				int d = 0;
				bool str = false;

				while (v < len && (j[v] == ' ' || j[v] == ':' || j[v] == '\t' ||
						   j[v] == '\r' || j[v] == '\n')) {
					v++;
				}
				for (e = v; e < len; e++) {
					char x = j[e];

					if (str) {
						if (x == '\\') {
							e++;
						} else if (x == '"') {
							str = false;
						}
						continue;
					}
					if (x == '"') {
						str = true;
					} else if (x == '{' || x == '[') {
						d++;
					} else if (x == '}' || x == ']') {
						if (d == 0) {
							break;
						}
						d--;
					} else if (x == ',' && d == 0) {
						break;
					}
				}
				while (e > v && (j[e - 1] == ' ' || j[e - 1] == '\n' ||
						 j[e - 1] == '\r' || j[e - 1] == '\t')) {
					e--;
				}
				if (e <= v || d != 0) {
					return -1;
				}
				*off = v;
				*vlen = e - v;
				return 0;
			}
		} else if (c == '{' || c == '[') {
			depth++;
		} else if (c == '}' || c == ']') {
			depth--;
		}
	}
	return -1;
}

int rook_http_parse(char *buf, size_t len, struct rook_http_resp *r)
{
	const char *end = buf + len, *line, *eol;
	long clen = -1;
	bool chunked = false;

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
			if (chunked) {
				long n = dechunk((char *)r->body, r->body_len);

				if (n < 0) {
					return -1;
				}
				r->body_len = (size_t)n;
				return 0;
			}
			if (clen >= 0 && (size_t)clen < r->body_len) {
				r->body_len = (size_t)clen;
			}
			return 0;
		}
		if (strncasecmp(line, "Retry-After:", 12) == 0) {
			r->retry_after_s = (int32_t)atol(line + 12);
		} else if (strncasecmp(line, "Content-Length:", 15) == 0) {
			clen = atol(line + 15);
		} else if (strncasecmp(line, "Transfer-Encoding:", 18) == 0) {
			chunked = strstr(line, "chunked") != NULL && strstr(line, "chunked") < eol;
		} else if (strncasecmp(line, "Date:", 5) == 0) {
			int64_t t = rook_http_date(line + 5, (size_t)(eol - line - 5) -
							      (eol[-1] == '\r' ? 1 : 0));

			if (t >= 0) {
				r->has_date = true;
				r->date = t;
			}
		}
		line = eol;
	}
	return -1;
}
