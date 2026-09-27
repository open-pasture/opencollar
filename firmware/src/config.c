#include "config.h"

#include <string.h>

#include "command.h"
#include "store.h"

#define CONFIG_MAGIC 0x3143434fu /* "OCC1" */
#define CONFIG_FORMAT 1

#define F_HAS 0x01
#define F_HERD 0x02
#define F_FAST 0x04
#define F_FAST_UNTIL 0x08
#define F_ENDPOINT 0x10
#define F_TRYING 0x20
#define F_TRIAL_SINCE 0x40

/* magic, format, flags, herd length, pad, version, report_s, poll_s,
 * fast_report_s, fast_poll_s, fast_until, trial_since, herd, endpoint, trial, crc */
#define OFF_VERSION 8
#define OFF_REPORT 12
#define OFF_POLL 16
#define OFF_FAST_REPORT 20
#define OFF_FAST_POLL 24
#define OFF_FAST_UNTIL 28
#define OFF_TRIAL_SINCE 36
#define OFF_HERD 44
#define OFF_ENDPOINT (OFF_HERD + PROTO_MAX_ID_BYTES)
#define OFF_TRIAL (OFF_ENDPOINT + PROTO_MAX_ENDPOINT_BYTES + 1)
#define OFF_CRC (OFF_TRIAL + PROTO_MAX_ENDPOINT_BYTES + 1)
#define CONFIG_BYTES (OFF_CRC + 4)

static uint8_t buf[CONFIG_BYTES];

static void put32(uint8_t *p, uint32_t v)
{
	for (int k = 0; k < 4; k++) {
		p[k] = (uint8_t)(v >> (8 * k));
	}
}

static uint32_t get32(const uint8_t *p)
{
	return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static void put64(uint8_t *p, int64_t v)
{
	put32(p, (uint32_t)v);
	put32(p + 4, (uint32_t)((uint64_t)v >> 32));
}

static int64_t get64(const uint8_t *p)
{
	return (int64_t)((uint64_t)get32(p) | (uint64_t)get32(p + 4) << 32);
}

/* ---- Parsing and checks ---- */

static bool opt_u32(const char *w, const struct wire_span *sp, bool *has, uint32_t *v)
{
	*has = false;
	if (!sp || wire_is_null(w + sp->val, sp->val_len)) {
		return true;
	}
	*has = wire_u32(w + sp->val, sp->val_len, v);
	return *has;
}

enum reject_code config_parse(const char *wire, size_t len, const uint8_t public_key[32],
			      struct config_cmd *out)
{
	struct wire_scan sc;
	enum reject_code code = wire_verify(wire, len, public_key, &sc);
	const struct wire_span *sp;

	if (code != REJECT_NONE) {
		return code;
	}
	memset(out, 0, sizeof(*out));

	if (!wire_read_id(wire, wire_find(wire, &sc, "command_id"), false, NULL,
			  &out->command_id) ||
	    !wire_read_id(wire, wire_find(wire, &sc, "collar_id"), false, NULL,
			  &out->collar_id) ||
	    !wire_read_id(wire, wire_find(wire, &sc, "herd_id"), true, &out->has_herd,
			  &out->herd_id)) {
		return REJECT_BAD_JSON;
	}

	sp = wire_find(wire, &sc, "version");
	if (!sp || !wire_u32(wire + sp->val, sp->val_len, &out->version)) {
		return REJECT_BAD_JSON;
	}
	sp = wire_find(wire, &sc, "report_s");
	if (!sp || !wire_u32(wire + sp->val, sp->val_len, &out->report_s)) {
		return REJECT_BAD_JSON;
	}
	sp = wire_find(wire, &sc, "poll_s");
	if (!sp || !wire_u32(wire + sp->val, sp->val_len, &out->poll_s)) {
		return REJECT_BAD_JSON;
	}
	if (!opt_u32(wire, wire_find(wire, &sc, "fast_report_s"), &out->has_fast_report,
		     &out->fast_report_s) ||
	    !opt_u32(wire, wire_find(wire, &sc, "fast_poll_s"), &out->has_fast_poll,
		     &out->fast_poll_s) ||
	    !wire_read_time(wire, wire_find(wire, &sc, "fast_until"), &out->has_fast_until,
			    &out->fast_until)) {
		return REJECT_BAD_JSON;
	}

	sp = wire_find(wire, &sc, "endpoint");
	if (sp && !wire_is_null(wire + sp->val, sp->val_len)) {
		if (!wire_string(wire + sp->val, sp->val_len, out->endpoint,
				 PROTO_MAX_ENDPOINT_BYTES, &out->endpoint_len)) {
			return REJECT_BAD_JSON;
		}
		out->has_endpoint = true;
		out->endpoint[out->endpoint_len > PROTO_MAX_ENDPOINT_BYTES ? PROTO_MAX_ENDPOINT_BYTES
									   : out->endpoint_len] =
			'\0';
	}
	return REJECT_NONE;
}

static bool interval_ok(uint32_t s)
{
	return s >= CONFIG_MIN_INTERVAL_S && s <= CONFIG_MAX_INTERVAL_S;
}

enum reject_code config_check(const struct config_cmd *c, const struct proto_id *collar_id,
			      bool has_held, uint32_t held_version)
{
	if (!proto_id_eq(&c->collar_id, collar_id)) {
		return REJECT_WRONG_COLLAR;
	}
	if (has_held && c->version <= held_version) {
		return REJECT_STALE;
	}
	if (!interval_ok(c->report_s) || !interval_ok(c->poll_s) ||
	    (c->has_fast_report && !interval_ok(c->fast_report_s)) ||
	    (c->has_fast_poll && !interval_ok(c->fast_poll_s))) {
		return REJECT_BAD_CONFIG;
	}
	if (c->has_fast_until && !(c->has_fast_report && c->has_fast_poll)) {
		return REJECT_BAD_CONFIG;
	}
	if (c->has_endpoint &&
	    (c->endpoint_len > PROTO_MAX_ENDPOINT_BYTES || c->endpoint_len <= 8 ||
	     memcmp(c->endpoint, "https://", 8) != 0)) {
		return REJECT_BAD_CONFIG;
	}
	return REJECT_NONE;
}

/* ---- State ---- */

void config_init(struct config *c)
{
	memset(c, 0, sizeof(*c));
	c->report_s = CONFIG_DEFAULT_INTERVAL_S;
	c->poll_s = CONFIG_DEFAULT_INTERVAL_S;
}

static void put_str(uint8_t *p, const char *s)
{
	size_t n = strlen(s);

	memset(p, 0, PROTO_MAX_ENDPOINT_BYTES + 1);
	memcpy(p, s, n);
}

static bool get_str(const uint8_t *p, char *out)
{
	if (memchr(p, '\0', PROTO_MAX_ENDPOINT_BYTES + 1) == NULL) {
		return false;
	}
	memcpy(out, p, PROTO_MAX_ENDPOINT_BYTES + 1);
	return true;
}

static void save(struct config *c)
{
	uint8_t flags = 0;

	memset(buf, 0, sizeof(buf));
	flags |= c->has ? F_HAS : 0;
	flags |= c->has_herd ? F_HERD : 0;
	flags |= c->has_fast ? F_FAST : 0;
	flags |= c->has_fast_until ? F_FAST_UNTIL : 0;
	flags |= c->has_endpoint ? F_ENDPOINT : 0;
	flags |= c->trying ? F_TRYING : 0;
	flags |= c->has_trial_since ? F_TRIAL_SINCE : 0;

	put32(buf, CONFIG_MAGIC);
	buf[4] = CONFIG_FORMAT;
	buf[5] = flags;
	buf[6] = c->herd.len;
	put32(buf + OFF_VERSION, c->version);
	put32(buf + OFF_REPORT, c->report_s);
	put32(buf + OFF_POLL, c->poll_s);
	put32(buf + OFF_FAST_REPORT, c->fast_report_s);
	put32(buf + OFF_FAST_POLL, c->fast_poll_s);
	put64(buf + OFF_FAST_UNTIL, c->fast_until);
	put64(buf + OFF_TRIAL_SINCE, c->trial_since);
	memcpy(buf + OFF_HERD, c->herd.s, c->herd.len);
	put_str(buf + OFF_ENDPOINT, c->endpoint);
	put_str(buf + OFF_TRIAL, c->trial);
	put32(buf + OFF_CRC, proto_crc32(0, buf, OFF_CRC));
	if (store_write(STORE_ID_CONFIG, buf, CONFIG_BYTES) != 0) {
		c->store_errors++;
	}
}

void config_load(struct config *c)
{
	int len = store_read(STORE_ID_CONFIG, buf, sizeof(buf));
	struct config t;

	config_init(c);
	if (len != CONFIG_BYTES || get32(buf) != CONFIG_MAGIC || buf[4] != CONFIG_FORMAT ||
	    get32(buf + OFF_CRC) != proto_crc32(0, buf, OFF_CRC)) {
		return;
	}

	uint8_t flags = buf[5];

	config_init(&t);
	t.has = flags & F_HAS;
	t.has_herd = flags & F_HERD;
	t.has_fast = flags & F_FAST;
	t.has_fast_until = flags & F_FAST_UNTIL;
	t.has_endpoint = flags & F_ENDPOINT;
	t.trying = flags & F_TRYING;
	t.has_trial_since = flags & F_TRIAL_SINCE;
	t.version = get32(buf + OFF_VERSION);
	t.report_s = get32(buf + OFF_REPORT);
	t.poll_s = get32(buf + OFF_POLL);
	t.fast_report_s = get32(buf + OFF_FAST_REPORT);
	t.fast_poll_s = get32(buf + OFF_FAST_POLL);
	t.fast_until = get64(buf + OFF_FAST_UNTIL);
	t.trial_since = get64(buf + OFF_TRIAL_SINCE);
	if (t.has_herd && !proto_id_set(&t.herd, (const char *)buf + OFF_HERD, buf[6])) {
		return;
	}
	if (!get_str(buf + OFF_ENDPOINT, t.endpoint) || !get_str(buf + OFF_TRIAL, t.trial) ||
	    !interval_ok(t.report_s) || !interval_ok(t.poll_s)) {
		return;
	}
	*c = t;
}

void config_wipe(struct config *c)
{
	config_init(c);
	if (store_delete(STORE_ID_CONFIG) != 0) {
		c->store_errors++;
	}
}

const char *config_endpoint(const struct config *c, const char *base_endpoint)
{
	if (c->trying) {
		return c->trial;
	}
	return c->has_endpoint ? c->endpoint : base_endpoint;
}

enum reject_code config_receive(struct config *c, const char *wire, size_t len,
				const uint8_t public_key[32], const struct proto_id *collar_id,
				const char *base_endpoint, bool has_now, int64_t now)
{
	struct config_cmd cmd;
	enum reject_code code = config_parse(wire, len, public_key, &cmd);

	if (code == REJECT_NONE) {
		code = config_check(&cmd, collar_id, c->has, c->version);
	}
	if (code != REJECT_NONE) {
		struct wire_scan sc;
		const struct wire_span *sp;
		uint32_t v = 0;

		/* Best effort for the report: the version as sent, if it can be read */
		if (wire_scan(wire, len, &sc) == REJECT_NONE &&
		    (sp = wire_find(wire, &sc, "version")) != NULL) {
			wire_u32(wire + sp->val, sp->val_len, &v);
		}
		c->has_reject = true;
		c->reject_version = v;
		c->reject_code = code;
		return code;
	}

	/* Where reports go now, before this config */
	const char *current = c->has_endpoint ? c->endpoint : base_endpoint;

	c->has = true;
	c->version = cmd.version;
	if (cmd.has_herd) {
		c->has_herd = true;
		c->herd = cmd.herd_id;
	}
	c->report_s = cmd.report_s;
	c->poll_s = cmd.poll_s;
	c->has_fast = cmd.has_fast_report && cmd.has_fast_poll;
	c->fast_report_s = c->has_fast ? cmd.fast_report_s : 0;
	c->fast_poll_s = c->has_fast ? cmd.fast_poll_s : 0;
	c->has_fast_until = cmd.has_fast_until;
	c->fast_until = cmd.has_fast_until ? cmd.fast_until : 0;

	if (cmd.has_endpoint) {
		if (strcmp(cmd.endpoint, current) == 0) {
			c->trying = false; /* Back to the one in use: nothing to try */
			c->has_trial_since = false;
		} else if (!c->trying || strcmp(cmd.endpoint, c->trial) != 0) {
			c->trying = true;
			strcpy(c->trial, cmd.endpoint);
			c->has_trial_since = has_now;
			c->trial_since = has_now ? now : 0;
		}
	}
	save(c);
	return REJECT_NONE;
}

void config_report_result(struct config *c, bool ok, bool has_now, int64_t now)
{
	if (!c->trying) {
		return;
	}
	if (ok) {
		/* The new endpoint works: it becomes the endpoint */
		strcpy(c->endpoint, c->trial);
		c->has_endpoint = true;
		c->trying = false;
		c->has_trial_since = false;
		c->trial[0] = '\0';
		save(c);
		return;
	}
	if (!has_now) {
		return;
	}
	if (!c->has_trial_since) {
		c->has_trial_since = true;
		c->trial_since = now;
		save(c);
	} else if (now - c->trial_since >= CONFIG_ENDPOINT_FALLBACK_S) {
		/* Failed for a day: back to the previous endpoint */
		c->trying = false;
		c->has_trial_since = false;
		c->trial[0] = '\0';
		save(c);
	}
}

void config_cadence(const struct config *c, bool has_now, int64_t now, uint32_t *report_s,
		    uint32_t *poll_s)
{
	if (c->has_fast && c->has_fast_until && has_now && now < c->fast_until) {
		*report_s = c->fast_report_s;
		*poll_s = c->fast_poll_s;
	} else {
		*report_s = c->report_s;
		*poll_s = c->poll_s;
	}
}
