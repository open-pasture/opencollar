#include "protocol.h"

#include <string.h>

const struct collar_limits LIMITS_LEGACY = {64, 0, 0, 64, 2, 0};
const struct collar_limits LIMITS_V0 = {128, 16, 32, 384, 16, 24576};
const struct collar_limits LIMITS_V1 = {128, 16, 32, 384, 32, 262144};

static const char *const codes[REJECT_COUNT] = {
	[REJECT_NONE] = "",
	[REJECT_BAD_SIG] = "bad_sig",
	[REJECT_WRONG_HERD] = "wrong_herd",
	[REJECT_WRONG_COLLAR] = "wrong_collar",
	[REJECT_BAD_JSON] = "bad_json",
	[REJECT_TOO_LARGE] = "too_large",
	[REJECT_STALE] = "stale",
	[REJECT_OUT_OF_RANGE] = "out_of_range",
	[REJECT_TOO_FEW_VERTICES] = "too_few_vertices",
	[REJECT_TOO_MANY_VERTICES] = "too_many_vertices",
	[REJECT_TOO_MANY_HOLES] = "too_many_holes",
	[REJECT_SELF_INTERSECTING] = "self_intersecting",
	[REJECT_RINGS_CROSS] = "rings_cross",
	[REJECT_HOLE_OUTSIDE] = "hole_outside",
	[REJECT_HOLES_OVERLAP] = "holes_overlap",
	[REJECT_ZERO_AREA] = "zero_area",
	[REJECT_HOLE_TOO_SMALL] = "hole_too_small",
	[REJECT_HOLE_TOO_CLOSE] = "hole_too_close",
	[REJECT_BAD_MARGINS] = "bad_margins",
	[REJECT_SLOTS_FULL] = "slots_full",
	[REJECT_BAD_CONFIG] = "bad_config",
};

const char *reject_str(enum reject_code code)
{
	return (unsigned)code < REJECT_COUNT ? codes[code] : "";
}

enum reject_code reject_parse(const char *s)
{
	for (int i = 1; i < REJECT_COUNT; i++) {
		if (strcmp(codes[i], s) == 0) {
			return (enum reject_code)i;
		}
	}
	return REJECT_NONE;
}

bool proto_id_eq(const struct proto_id *a, const struct proto_id *b)
{
	return a->len == b->len && memcmp(a->s, b->s, a->len) == 0;
}

bool proto_id_set(struct proto_id *id, const char *s, size_t len)
{
	memset(id, 0, sizeof(*id));
	if (len == 0 || len > PROTO_MAX_ID_BYTES) {
		return false;
	}
	memcpy(id->s, s, len);
	id->len = (uint8_t)len;
	return true;
}

/* Days since 1970-01-01 of a proleptic Gregorian date (Howard Hinnant's days_from_civil) */
static int64_t days_from_civil(int64_t y, int64_t m, int64_t d)
{
	y -= m <= 2;
	int64_t era = (y >= 0 ? y : y - 399) / 400;
	int64_t yoe = y - era * 400;
	int64_t doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
	int64_t doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;

	return era * 146097 + doe - 719468;
}

static void civil_from_days(int64_t z, int64_t *y, int *m, int *d)
{
	z += 719468;
	int64_t era = (z >= 0 ? z : z - 146096) / 146097;
	int64_t doe = z - era * 146097;
	int64_t yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
	int64_t doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
	int64_t mp = (5 * doy + 2) / 153;

	*d = (int)(doy - (153 * mp + 2) / 5 + 1);
	*m = (int)(mp < 10 ? mp + 3 : mp - 9);
	*y = yoe + era * 400 + (*m <= 2);
}

static bool digits(const char *s, int n, int *out)
{
	int v = 0;

	for (int i = 0; i < n; i++) {
		if (s[i] < '0' || s[i] > '9') {
			return false;
		}
		v = v * 10 + (s[i] - '0');
	}
	*out = v;
	return true;
}

static int days_in_month(int y, int m)
{
	static const int dim[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
	bool leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;

	return m == 2 && leap ? 29 : dim[m - 1];
}

int64_t proto_time_civil(int year, int month, int day, int hour, int minute, int second)
{
	return days_from_civil(year, month, day) * 86400 + hour * 3600 + minute * 60 + second;
}

bool proto_time_parse(const char *s, size_t len, int64_t *out)
{
	int y, mo, d, h, mi, se;
	size_t i = 19;

	if (len < 20 || s[4] != '-' || s[7] != '-' || s[13] != ':' || s[16] != ':' ||
	    (s[10] != 'T' && s[10] != 't')) {
		return false;
	}
	if (!digits(s, 4, &y) || !digits(s + 5, 2, &mo) || !digits(s + 8, 2, &d) ||
	    !digits(s + 11, 2, &h) || !digits(s + 14, 2, &mi) || !digits(s + 17, 2, &se)) {
		return false;
	}
	if (mo < 1 || mo > 12 || d < 1 || d > days_in_month(y, mo) || h > 23 || mi > 59 ||
	    se > 60) {
		return false;
	}
	if (s[i] == '.') {
		size_t start = ++i;

		while (i < len && s[i] >= '0' && s[i] <= '9') {
			i++;
		}
		if (i == start) {
			return false;
		}
	}

	int64_t offset = 0;

	if (i < len && (s[i] == 'Z' || s[i] == 'z')) {
		i++;
	} else if (i + 6 == len && (s[i] == '+' || s[i] == '-') && s[i + 3] == ':') {
		int oh, om;

		if (!digits(s + i + 1, 2, &oh) || !digits(s + i + 4, 2, &om) || oh > 23 ||
		    om > 59) {
			return false;
		}
		offset = (int64_t)(oh * 3600 + om * 60) * (s[i] == '+' ? 1 : -1);
		i += 6;
	} else {
		return false;
	}
	if (i != len) {
		return false;
	}
	if (se == 60) {
		se = 59; /* A leap second counts as the second before it */
	}
	*out = days_from_civil(y, mo, d) * 86400 + h * 3600 + mi * 60 + se - offset;
	return true;
}

int proto_time_format(int64_t t, char *out, size_t cap)
{
	int64_t days = t >= 0 ? t / 86400 : -((-t + 86399) / 86400);
	int64_t secs = t - days * 86400;
	int64_t y;
	int m, d;

	civil_from_days(days, &y, &m, &d);
	if (cap < 21 || y < 0 || y > 9999) {
		if (cap > 0) {
			out[0] = '\0';
		}
		return 0;
	}

	int h = (int)(secs / 3600), mi = (int)(secs / 60 % 60), s = (int)(secs % 60);
	int v[6] = {(int)y, m, d, h, mi, s};
	const char *sep = "--T::Z";
	int widths[6] = {4, 2, 2, 2, 2, 2};
	int n = 0;

	for (int k = 0; k < 6; k++) {
		for (int w = widths[k] - 1, x = v[k]; w >= 0; w--, x /= 10) {
			out[n + w] = (char)('0' + x % 10);
		}
		n += widths[k];
		out[n++] = sep[k];
	}
	out[n] = '\0';
	return n;
}

uint32_t proto_crc32(uint32_t crc, const void *data, size_t len)
{
	const uint8_t *p = data;

	crc = ~crc;
	while (len--) {
		crc ^= *p++;
		for (int k = 0; k < 8; k++) {
			crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
		}
	}
	return ~crc;
}

static int b64_value(char c)
{
	if (c >= 'A' && c <= 'Z') {
		return c - 'A';
	}
	if (c >= 'a' && c <= 'z') {
		return c - 'a' + 26;
	}
	if (c >= '0' && c <= '9') {
		return c - '0' + 52;
	}
	if (c == '+') {
		return 62;
	}
	if (c == '/') {
		return 63;
	}
	return -1;
}

int proto_base64_decode(const char *in, size_t len, uint8_t *out, size_t cap)
{
	size_t n = 0;

	if (len % 4 != 0) {
		return -1;
	}
	for (size_t i = 0; i < len; i += 4) {
		bool last = i + 4 == len;
		int pad = 0;
		int v[4];

		for (int k = 0; k < 4; k++) {
			if (in[i + k] == '=') {
				/* Padding only at the end, only in the last two places */
				if (!last || k < 2) {
					return -1;
				}
				v[k] = 0;
				pad++;
			} else {
				if (pad) {
					return -1;
				}
				v[k] = b64_value(in[i + k]);
				if (v[k] < 0) {
					return -1;
				}
			}
		}

		uint32_t w = (uint32_t)v[0] << 18 | (uint32_t)v[1] << 12 | (uint32_t)v[2] << 6 |
			     (uint32_t)v[3];
		int bytes = 3 - pad;

		/* Unused bits must be zero */
		if ((pad == 1 && (w & 0xff)) || (pad == 2 && (w & 0xffff))) {
			return -1;
		}
		if (n + (size_t)bytes > cap) {
			return -1;
		}
		for (int k = 0; k < bytes; k++) {
			out[n++] = (uint8_t)(w >> (16 - 8 * k));
		}
	}
	return (int)n;
}
