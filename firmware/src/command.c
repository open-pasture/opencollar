#include "command.h"

#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "monocypher-ed25519.h"
#include "monocypher.h"

/* Deepest array nesting: holes need 3 ([[[lon, lat]]]), plus one spare */
#define MAX_ARRAY_DEPTH 4

/* ---- UTF-8 (strict, as Rust's str::from_utf8) ---- */

static bool utf8_valid(const uint8_t *s, size_t n)
{
	size_t i = 0;

	while (i < n) {
		uint8_t c = s[i];
		size_t k;
		uint8_t lo = 0x80, hi = 0xbf;

		if (c < 0x80) {
			i++;
			continue;
		} else if (c >= 0xc2 && c <= 0xdf) {
			k = 1;
		} else if (c >= 0xe0 && c <= 0xef) {
			k = 2;
			if (c == 0xe0) {
				lo = 0xa0;
			} else if (c == 0xed) {
				hi = 0x9f;
			}
		} else if (c >= 0xf0 && c <= 0xf4) {
			k = 3;
			if (c == 0xf0) {
				lo = 0x90;
			} else if (c == 0xf4) {
				hi = 0x8f;
			}
		} else {
			return false;
		}
		if (i + k >= n) {
			return false; /* Truncated sequence */
		}
		if (s[i + 1] < lo || s[i + 1] > hi) {
			return false;
		}
		for (size_t j = 2; j <= k; j++) {
			if (s[i + j] < 0x80 || s[i + j] > 0xbf) {
				return false;
			}
		}
		i += k + 1;
	}
	return true;
}

/* ---- The span scanner (port of op_protocol::wire::Scanner) ---- */

struct scanner {
	const char *b;
	size_t n, i;
};

static void ws(struct scanner *s)
{
	while (s->i < s->n &&
	       (s->b[s->i] == ' ' || s->b[s->i] == '\t' || s->b[s->i] == '\n' || s->b[s->i] == '\r')) {
		s->i++;
	}
}

static int peek(const struct scanner *s)
{
	return s->i < s->n ? (unsigned char)s->b[s->i] : -1;
}

static bool is_digit(int c)
{
	return c >= '0' && c <= '9';
}

static bool is_hex(int c)
{
	return is_digit(c) || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
}

/* A string token, quotes and escapes included */
static bool scan_string(struct scanner *s)
{
	if (peek(s) != '"') {
		return false;
	}
	s->i++;
	for (;;) {
		int c = peek(s);

		if (c < 0) {
			return false;
		}
		if (c == '"') {
			s->i++;
			return true;
		}
		if (c == '\\') {
			s->i++;
			c = peek(s);
			if (c == '"' || c == '\\' || c == '/' || c == 'b' || c == 'f' || c == 'n' ||
			    c == 'r' || c == 't') {
				s->i++;
			} else if (c == 'u') {
				if (s->i + 5 > s->n) {
					return false;
				}
				for (int k = 1; k <= 4; k++) {
					if (!is_hex((unsigned char)s->b[s->i + k])) {
						return false;
					}
				}
				s->i += 5;
			} else {
				return false;
			}
		} else if (c < 0x20) {
			return false;
		} else {
			s->i++;
		}
	}
}

static size_t scan_digits(struct scanner *s)
{
	size_t from = s->i;

	while (is_digit(peek(s))) {
		s->i++;
	}
	return s->i - from;
}

/* -?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)? */
static bool scan_number(struct scanner *s)
{
	if (peek(s) == '-') {
		s->i++;
	}
	if (peek(s) == '0') {
		s->i++;
	} else if (peek(s) >= '1' && peek(s) <= '9') {
		scan_digits(s);
	} else {
		return false;
	}
	if (peek(s) == '.') {
		s->i++;
		if (scan_digits(s) == 0) {
			return false;
		}
	}
	if (peek(s) == 'e' || peek(s) == 'E') {
		s->i++;
		if (peek(s) == '+' || peek(s) == '-') {
			s->i++;
		}
		if (scan_digits(s) == 0) {
			return false;
		}
	}
	return true;
}

static bool scan_literal(struct scanner *s, const char *lit)
{
	size_t n = strlen(lit);

	if (s->n - s->i < n || memcmp(s->b + s->i, lit, n) != 0) {
		return false;
	}
	s->i += n;
	return true;
}

static bool scan_value(struct scanner *s, int depth)
{
	switch (peek(s)) {
	case '"':
		return scan_string(s);
	case '[':
		if (depth == MAX_ARRAY_DEPTH) {
			return false;
		}
		s->i++;
		ws(s);
		if (peek(s) == ']') {
			s->i++;
			return true;
		}
		for (;;) {
			ws(s);
			if (!scan_value(s, depth + 1)) {
				return false;
			}
			ws(s);
			if (peek(s) == ',') {
				s->i++;
			} else if (peek(s) == ']') {
				s->i++;
				return true;
			} else {
				return false;
			}
		}
	case 't':
		return scan_literal(s, "true");
	case 'f':
		return scan_literal(s, "false");
	case 'n':
		return scan_literal(s, "null");
	default:
		if (peek(s) == '-' || is_digit(peek(s))) {
			return scan_number(s);
		}
		return false; /* '{' (a nested object) and anything else */
	}
}

static bool scan_object(struct scanner *s, struct wire_scan *out)
{
	out->n = 0;
	out->sig = -1;
	ws(s);
	if (peek(s) != '{') {
		return false;
	}
	s->i++;
	ws(s);
	if (peek(s) == '}') {
		s->i++;
	} else {
		for (;;) {
			ws(s);

			size_t kstart = s->i;

			if (!scan_string(s)) {
				return false;
			}

			size_t key = kstart + 1, key_len = s->i - kstart - 2;

			if (memchr(s->b + key, '\\', key_len)) {
				return false;
			}
			ws(s);
			if (peek(s) != ':') {
				return false;
			}
			s->i++;
			ws(s);

			size_t vstart = s->i;

			if (!scan_value(s, 0)) {
				return false;
			}
			if (out->n == PROTO_MAX_KEYS) {
				return false;
			}
			for (int k = 0; k < out->n; k++) {
				if (out->span[k].key_len == key_len &&
				    memcmp(s->b + out->span[k].key, s->b + key, key_len) == 0) {
					return false;
				}
			}
			out->span[out->n] = (struct wire_span){
				.key = (uint16_t)key,
				.key_len = (uint16_t)key_len,
				.val = (uint16_t)vstart,
				.val_len = (uint16_t)(s->i - vstart),
			};
			if (key_len == 3 && memcmp(s->b + key, "sig", 3) == 0) {
				out->sig = (int8_t)out->n;
			}
			out->n++;
			ws(s);
			if (peek(s) == ',') {
				s->i++;
			} else if (peek(s) == '}') {
				s->i++;
				break;
			} else {
				return false;
			}
		}
	}
	ws(s);
	return s->i == s->n;
}

enum reject_code wire_scan(const char *w, size_t len, struct wire_scan *out)
{
	struct scanner s = {.b = w, .n = len, .i = 0};

	if (len > PROTO_MAX_COMMAND_BYTES) {
		return REJECT_TOO_LARGE;
	}
	if (!utf8_valid((const uint8_t *)w, len)) {
		return REJECT_BAD_JSON;
	}
	return scan_object(&s, out) ? REJECT_NONE : REJECT_BAD_JSON;
}

const struct wire_span *wire_find(const char *w, const struct wire_scan *sc, const char *key)
{
	size_t n = strlen(key);

	for (int k = 0; k < sc->n; k++) {
		if (sc->span[k].key_len == n && memcmp(w + sc->span[k].key, key, n) == 0) {
			return &sc->span[k];
		}
	}
	return NULL;
}

/* ---- Canonical bytes ---- */

static int key_cmp(const char *w, const struct wire_span *a, const struct wire_span *b)
{
	size_t n = a->key_len < b->key_len ? a->key_len : b->key_len;
	int c = memcmp(w + a->key, w + b->key, n);

	if (c != 0) {
		return c;
	}
	return (a->key_len > b->key_len) - (a->key_len < b->key_len);
}

/* A value token with whitespace outside strings removed */
static void emit_value(const char *w, const struct wire_span *sp, wire_sink sink, void *ctx)
{
	const char *t = w + sp->val;
	size_t n = sp->val_len, run = 0;
	bool in_str = false;

	for (size_t i = 0; i < n; i++) {
		char c = t[i];

		if (in_str) {
			if (c == '\\') {
				i++; /* The escaped character never ends the string */
			} else if (c == '"') {
				in_str = false;
			}
			continue;
		}
		if (c == '"') {
			in_str = true;
		} else if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
			if (i > run) {
				sink(ctx, (const uint8_t *)t + run, i - run);
			}
			run = i + 1;
		}
	}
	if (n > run) {
		sink(ctx, (const uint8_t *)t + run, n - run);
	}
}

void wire_canonical(const char *w, const struct wire_scan *sc, wire_sink sink, void *ctx)
{
	uint8_t order[PROTO_MAX_KEYS];
	int n = 0;

	for (int k = 0; k < sc->n; k++) {
		if (k == sc->sig) {
			continue;
		}

		int j = n++;

		while (j > 0 && key_cmp(w, &sc->span[order[j - 1]], &sc->span[k]) > 0) {
			order[j] = order[j - 1];
			j--;
		}
		order[j] = (uint8_t)k;
	}

	sink(ctx, (const uint8_t *)"{", 1);
	for (int j = 0; j < n; j++) {
		const struct wire_span *sp = &sc->span[order[j]];

		if (j > 0) {
			sink(ctx, (const uint8_t *)",", 1);
		}
		sink(ctx, (const uint8_t *)"\"", 1);
		sink(ctx, (const uint8_t *)w + sp->key, sp->key_len);
		sink(ctx, (const uint8_t *)"\":", 2);
		emit_value(w, sp, sink, ctx);
	}
	sink(ctx, (const uint8_t *)"}", 1);
}

static void sha_sink(void *ctx, const uint8_t *p, size_t n)
{
	crypto_sha512_update(ctx, p, n);
}

enum reject_code wire_verify(const char *w, size_t len, const uint8_t public_key[32],
			     struct wire_scan *out)
{
	enum reject_code code = wire_scan(w, len, out);

	if (code != REJECT_NONE) {
		return code;
	}
	if (out->sig < 0) {
		return REJECT_BAD_SIG;
	}

	const struct wire_span *sp = &out->span[out->sig];
	const char *t = w + sp->val;
	uint8_t sig[64];

	if (sp->val_len < 2 || t[0] != '"' || t[sp->val_len - 1] != '"' ||
	    memchr(t + 1, '\\', sp->val_len - 2) ||
	    proto_base64_decode(t + 1, sp->val_len - 2, sig, sizeof(sig)) != 64) {
		return REJECT_BAD_SIG;
	}

	/* Ed25519: h = SHA-512(R || A || canonical) mod L, then check [S]B = R + [h]A */
	crypto_sha512_ctx sha;
	uint8_t hash[64], h_ram[32];

	crypto_sha512_init(&sha);
	crypto_sha512_update(&sha, sig, 32);
	crypto_sha512_update(&sha, public_key, 32);
	wire_canonical(w, out, sha_sink, &sha);
	crypto_sha512_final(&sha, hash);
	crypto_eddsa_reduce(h_ram, hash);

	return crypto_eddsa_check_equation(sig, public_key, h_ram) == 0 ? REJECT_NONE
									  : REJECT_BAD_SIG;
}

/* ---- Value tokens ---- */

bool wire_is_null(const char *t, size_t n)
{
	return n == 4 && memcmp(t, "null", 4) == 0;
}

static int hex4(const char *p)
{
	int v = 0;

	for (int k = 0; k < 4; k++) {
		char c = p[k];

		v <<= 4;
		if (c >= '0' && c <= '9') {
			v |= c - '0';
		} else if (c >= 'a' && c <= 'f') {
			v |= c - 'a' + 10;
		} else {
			v |= c - 'A' + 10;
		}
	}
	return v;
}

static void put(char *out, size_t cap, size_t *len, char c)
{
	if (*len < cap) {
		out[*len] = c;
	}
	(*len)++;
}

bool wire_string(const char *t, size_t n, char *out, size_t cap, size_t *len)
{
	*len = 0;
	if (n < 2 || t[0] != '"' || t[n - 1] != '"') {
		return false;
	}
	for (size_t i = 1; i < n - 1; i++) {
		char c = t[i];

		if (c != '\\') {
			put(out, cap, len, c);
			continue;
		}
		c = t[++i];
		switch (c) {
		case 'b':
			put(out, cap, len, '\b');
			break;
		case 'f':
			put(out, cap, len, '\f');
			break;
		case 'n':
			put(out, cap, len, '\n');
			break;
		case 'r':
			put(out, cap, len, '\r');
			break;
		case 't':
			put(out, cap, len, '\t');
			break;
		case 'u': {
			uint32_t cp = (uint32_t)hex4(t + i + 1);

			i += 4;
			if (cp >= 0xdc00 && cp <= 0xdfff) {
				return false; /* Lone trailing surrogate */
			}
			if (cp >= 0xd800 && cp <= 0xdbff) {
				if (i + 6 >= n - 1 || t[i + 1] != '\\' || t[i + 2] != 'u') {
					return false;
				}

				uint32_t lo = (uint32_t)hex4(t + i + 3);

				if (lo < 0xdc00 || lo > 0xdfff) {
					return false;
				}
				cp = 0x10000 + ((cp - 0xd800) << 10) + (lo - 0xdc00);
				i += 6;
			}
			if (cp < 0x80) {
				put(out, cap, len, (char)cp);
			} else if (cp < 0x800) {
				put(out, cap, len, (char)(0xc0 | cp >> 6));
				put(out, cap, len, (char)(0x80 | (cp & 0x3f)));
			} else if (cp < 0x10000) {
				put(out, cap, len, (char)(0xe0 | cp >> 12));
				put(out, cap, len, (char)(0x80 | ((cp >> 6) & 0x3f)));
				put(out, cap, len, (char)(0x80 | (cp & 0x3f)));
			} else {
				put(out, cap, len, (char)(0xf0 | cp >> 18));
				put(out, cap, len, (char)(0x80 | ((cp >> 12) & 0x3f)));
				put(out, cap, len, (char)(0x80 | ((cp >> 6) & 0x3f)));
				put(out, cap, len, (char)(0x80 | (cp & 0x3f)));
			}
			break;
		}
		default: /* '"', '\\', '/' */
			put(out, cap, len, c);
			break;
		}
	}
	return true;
}

bool wire_u32(const char *t, size_t n, uint32_t *out)
{
	size_t i = 0;
	uint64_t v = 0;
	bool neg = false;

	if (n > 0 && t[0] == '-') {
		neg = true;
		i++;
	}
	if (i == n) {
		return false;
	}
	for (; i < n; i++) {
		if (!is_digit((unsigned char)t[i])) {
			return false; /* A fraction or an exponent makes it a float */
		}
		v = v * 10 + (uint64_t)(t[i] - '0');
		if (v > UINT32_MAX) {
			return false;
		}
	}
	if (neg && v != 0) {
		return false;
	}
	*out = (uint32_t)v;
	return true;
}

bool wire_f64(const char *t, size_t n, double *out)
{
	char *end;
	double v;

	if (n == 0 || !(t[0] == '-' || is_digit((unsigned char)t[0]))) {
		return false;
	}
	/* The scanner checked the grammar and the token is followed by a
	 * delimiter, so strtod stops exactly at its end */
	errno = 0;
	v = strtod(t, &end);
	if (end != t + n || isinf(v)) {
		return false;
	}
	*out = v;
	return true;
}

bool wire_e7(const char *t, size_t n, int64_t limit_e7, int64_t *e7, bool *in_range)
{
	size_t i = 0;
	bool neg = false;

	if (i < n && t[i] == '-') {
		neg = true;
		i++;
	}

	size_t int_start = i;

	while (i < n && is_digit((unsigned char)t[i])) {
		i++;
	}

	size_t int_len = i - int_start, frac_start = i, frac_len = 0;

	if (int_len == 0) {
		return false;
	}
	if (i < n && t[i] == '.') {
		frac_start = ++i;
		while (i < n && is_digit((unsigned char)t[i])) {
			i++;
		}
		frac_len = i - frac_start;
		if (frac_len == 0) {
			return false;
		}
	}

	int64_t exp = 0;

	if (i < n && (t[i] == 'e' || t[i] == 'E')) {
		bool eneg = false;
		size_t from;

		i++;
		if (i < n && (t[i] == '+' || t[i] == '-')) {
			eneg = t[i] == '-';
			i++;
		}
		from = i;
		while (i < n && is_digit((unsigned char)t[i])) {
			if (exp < 100000000) {
				exp = exp * 10 + (t[i] - '0');
			}
			i++;
		}
		if (i == from) {
			return false;
		}
		if (eneg) {
			exp = -exp;
		}
	}
	if (i != n) {
		return false;
	}

	/* The value is the digit string D = int digits + frac digits times
	 * 10^(exp - frac_len); in e7 units, D x 10^s. */
	size_t total = int_len + frac_len;
	int64_t s = exp - (int64_t)frac_len + 7;
#define DIGIT(d) ((d) < int_len ? t[int_start + (d)] : t[frac_start + (d) - int_len])

	size_t z = 0;

	while (z < total && DIGIT(z) == '0') {
		z++;
	}
	if (z == total) {
		*e7 = 0;
		*in_range = true;
		return true;
	}

	int64_t k = (int64_t)(total - z); /* Significant digits */
	int64_t p = k + s;                /* Integer digits of the e7 value */

	/* The value is in [10^(p-8), 10^(p-7)): from 1e308 up it may not fit a double */
	if (p >= 316) {
		double v;

		if (p >= 317 || !wire_f64(t, n, &v)) {
			return false;
		}
	}
	if (p > 18) {
		*e7 = 0;
		*in_range = false; /* At least 1e11 degrees */
		return true;
	}

	uint64_t ip = 0;
	bool sticky = false;
	int round = 0;

	for (int64_t j = 0; j < p; j++) {
		int dg = j < k ? DIGIT(z + (size_t)j) - '0' : 0;

		ip = ip * 10 + (uint64_t)dg;
	}
	for (int64_t j = p < 0 ? 0 : p; j < k; j++) {
		int dg = DIGIT(z + (size_t)j) - '0';

		if (j == p) {
			round = dg;
		}
		if (dg != 0) {
			sticky = true;
		}
	}
	if (p < 0) {
		round = 0; /* Below a tenth of an e7 unit */
	}
#undef DIGIT

	*in_range = ip < (uint64_t)limit_e7 || (ip == (uint64_t)limit_e7 && !sticky);

	uint64_t r = ip + (round >= 5 ? 1 : 0);

	*e7 = neg ? -(int64_t)r : (int64_t)r;
	return true;
}

/* ---- Boundary command fields ---- */

struct cursor {
	const char *p, *end;
};

static void cws(struct cursor *c)
{
	while (c->p < c->end && (*c->p == ' ' || *c->p == '\t' || *c->p == '\n' || *c->p == '\r')) {
		c->p++;
	}
}

static bool ceat(struct cursor *c, char ch)
{
	cws(c);
	if (c->p < c->end && *c->p == ch) {
		c->p++;
		return true;
	}
	return false;
}

static bool cnumber(struct cursor *c, const char **tok, size_t *len)
{
	cws(c);

	const char *s = c->p;

	while (c->p < c->end && (is_digit((unsigned char)*c->p) || *c->p == '-' || *c->p == '+' ||
				 *c->p == '.' || *c->p == 'e' || *c->p == 'E')) {
		c->p++;
	}
	*tok = s;
	*len = (size_t)(c->p - s);
	return *len > 0 && (s[0] == '-' || is_digit((unsigned char)s[0]));
}

/* [lon, lat]: exactly two numbers */
static bool parse_pair(struct cursor *c, struct shape *sh)
{
	const char *lt, *at;
	size_t ln, an;
	int64_t lon, lat;
	bool lon_ok, lat_ok;

	if (!ceat(c, '[') || !cnumber(c, &lt, &ln) || !ceat(c, ',') || !cnumber(c, &at, &an) ||
	    !ceat(c, ']')) {
		return false;
	}
	if (!wire_e7(lt, ln, 1800000000, &lon, &lon_ok) ||
	    !wire_e7(at, an, 900000000, &lat, &lat_ok)) {
		return false;
	}
	shape_vertex(sh, lon, lat, lon_ok && lat_ok);
	return true;
}

/* [[lon, lat], ...] */
static bool parse_ring(struct cursor *c, struct shape *sh)
{
	if (!ceat(c, '[')) {
		return false;
	}
	shape_ring_begin(sh);
	if (!ceat(c, ']')) {
		do {
			if (!parse_pair(c, sh)) {
				return false;
			}
		} while (ceat(c, ','));
		if (!ceat(c, ']')) {
			return false;
		}
	}
	shape_ring_end(sh);
	return true;
}

static bool parse_rings(struct cursor *c, struct shape *sh)
{
	if (!ceat(c, '[')) {
		return false;
	}
	if (ceat(c, ']')) {
		return true;
	}
	do {
		if (!parse_ring(c, sh)) {
			return false;
		}
	} while (ceat(c, ','));
	return ceat(c, ']');
}

static bool span_cursor(const char *w, const struct wire_span *sp, struct cursor *c)
{
	c->p = w + sp->val;
	c->end = c->p + sp->val_len;
	return true;
}

bool wire_read_id(const char *w, const struct wire_span *sp, bool optional, bool *has,
		  struct proto_id *id)
{
	char buf[PROTO_MAX_ID_BYTES];
	size_t len;

	if (has) {
		*has = false;
	}
	if (!sp) {
		return optional;
	}
	if (optional && wire_is_null(w + sp->val, sp->val_len)) {
		return true;
	}
	if (!wire_string(w + sp->val, sp->val_len, buf, sizeof(buf), &len) ||
	    !proto_id_set(id, buf, len)) {
		return false;
	}
	if (has) {
		*has = true;
	}
	return true;
}

static bool read_margin(const char *w, const struct wire_span *sp, bool *has, double *v)
{
	*has = false;
	if (!sp || wire_is_null(w + sp->val, sp->val_len)) {
		return true;
	}
	*has = wire_f64(w + sp->val, sp->val_len, v);
	return *has;
}

bool wire_read_time(const char *w, const struct wire_span *sp, bool *has, int64_t *t)
{
	char buf[64];
	size_t len;

	*has = false;
	if (!sp || wire_is_null(w + sp->val, sp->val_len)) {
		return true;
	}
	if (!wire_string(w + sp->val, sp->val_len, buf, sizeof(buf), &len) || len > sizeof(buf) ||
	    !proto_time_parse(buf, len, t)) {
		return false;
	}
	*has = true;
	return true;
}

enum reject_code command_parse(const char *wire, size_t len, const uint8_t public_key[32],
			       struct boundary_cmd *cmd, int32_t (*buf)[2], uint16_t cap)
{
	struct wire_scan sc;
	enum reject_code code = wire_verify(wire, len, public_key, &sc);

	if (code != REJECT_NONE) {
		return code;
	}

	memset(cmd, 0, sizeof(*cmd));
	shape_init(&cmd->shape, buf, cap);

	const struct wire_span *sp;
	struct cursor c;

	if (!wire_read_id(wire, wire_find(wire, &sc, "command_id"), false, NULL,
			  &cmd->command_id) ||
	    !wire_read_id(wire, wire_find(wire, &sc, "herd_id"), true, &cmd->has_herd,
			  &cmd->herd_id) ||
	    !wire_read_id(wire, wire_find(wire, &sc, "collar_id"), true, &cmd->has_collar,
			  &cmd->collar_id)) {
		return REJECT_BAD_JSON;
	}

	sp = wire_find(wire, &sc, "version");
	if (!sp || !wire_u32(wire + sp->val, sp->val_len, &cmd->version)) {
		return REJECT_BAD_JSON;
	}
	if (!wire_read_time(wire, wire_find(wire, &sc, "effective_at"), &cmd->has_effective_at,
			    &cmd->effective_at)) {
		return REJECT_BAD_JSON;
	}

	/* The outer ring first, whatever the key order */
	sp = wire_find(wire, &sc, "boundary");
	if (!sp || !span_cursor(wire, sp, &c) || !parse_ring(&c, &cmd->shape) || c.p != c.end) {
		return REJECT_BAD_JSON;
	}
	sp = wire_find(wire, &sc, "holes");
	if (sp && (!span_cursor(wire, sp, &c) || !parse_rings(&c, &cmd->shape) || c.p != c.end)) {
		return REJECT_BAD_JSON;
	}

	sp = wire_find(wire, &sc, "cue_mode");
	if (sp) {
		char mode[8];
		size_t n;

		if (!wire_string(wire + sp->val, sp->val_len, mode, sizeof(mode), &n)) {
			return REJECT_BAD_JSON;
		}
		if (n == 5 && memcmp(mode, "track", 5) == 0) {
			cmd->track = true;
		} else if (!(n == 5 && memcmp(mode, "audio", 5) == 0)) {
			return REJECT_BAD_JSON;
		}
	}

	if (!read_margin(wire, wire_find(wire, &sc, "warn_m"), &cmd->has_warn, &cmd->warn_m) ||
	    !read_margin(wire, wire_find(wire, &sc, "hysteresis_m"), &cmd->has_hysteresis,
			 &cmd->hysteresis_m)) {
		return REJECT_BAD_JSON;
	}
	return REJECT_NONE;
}
