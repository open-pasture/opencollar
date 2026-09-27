#include "app.h"

#include <stdio.h>
#include <string.h>

static void apply_boundary(void *ctx, const struct slot_hdr *hdr, const int32_t (*v)[2])
{
	struct app *a = ctx;
	struct geofence *next = a->fence == &a->fences[0] ? &a->fences[1] : &a->fences[0];
	struct geofence_config cfg = a->defaults;

	cfg.warn_m = hdr->warn_m;
	cfg.hysteresis_m = hdr->hysteresis_m;

	/* Build into the scratch fence, then swap: the old one stays in force
	 * until the new one is complete */
	if (geofence_init_e7(next, &cfg, v, hdr->ring_len, hdr->rings, hdr->version) != 0) {
		return;
	}
	a->fence = next;
	cue_rearm_at(&a->cue, a->now_ms);
	cue_set_mode(&a->cue, (hdr->flags & SLOT_F_TRACK) ? CUE_MODE_TRACK : CUE_MODE_AUDIO);
}

void app_init(struct app *a, const struct cue_config *cue_cfg,
	      const struct geofence_config *defaults)
{
	memset(a, 0, sizeof(*a));
	a->defaults = *defaults;
	cue_init(&a->cue, cue_cfg);
	config_init(&a->cfg);
	slots_init(&a->slots, &LIMITS_V0, a->e7, apply_boundary, a);
	a->slots.warn_m = defaults->warn_m;
	a->slots.hysteresis_m = defaults->hysteresis_m;
}

const struct proto_id *app_herd(const struct app *a)
{
	if (!a->prov.ok) {
		return NULL;
	}
	return a->cfg.has_herd ? &a->cfg.herd : &a->prov.herd_id;
}

static void set_ids(struct app *a)
{
	slots_set_herd(&a->slots, app_herd(a));
	slots_set_collar(&a->slots, a->prov.ok ? &a->prov.collar_id : NULL);
}

void app_boot(struct app *a, int64_t now_ms)
{
	a->now_ms = now_ms;
	a->has_clock = false;
	a->fence = NULL;
	cue_rearm_at(&a->cue, now_ms);

	provision_load(&a->prov);
	if (!a->prov.ok) {
		return; /* GNSS only */
	}
	config_load(&a->cfg);
	set_ids(a);
	slots_load(&a->slots);
	acks_load(&a->acks);
}

bool app_bench(struct app *a, const struct geo_point *vertices, int n, int64_t now_ms)
{
	struct geofence *next = a->fence == &a->fences[0] ? &a->fences[1] : &a->fences[0];

	if (a->fence) {
		return false;
	}
	if (geofence_init(next, &a->defaults, vertices, n, 0) != 0) {
		return false;
	}
	a->fence = next;
	cue_rearm_at(&a->cue, now_ms);
	cue_set_mode(&a->cue, CUE_MODE_AUDIO);
	return true;
}

bool app_now(const struct app *a, int64_t now_ms, int64_t *utc)
{
	if (!a->has_clock) {
		return false;
	}
	*utc = a->clock_utc + (now_ms - a->clock_ms) / 1000;
	return true;
}

struct app_fix_out app_fix(struct app *a, const struct app_fix_in *f, int64_t now_ms)
{
	struct app_fix_out out = {0};

	a->now_ms = now_ms;
	if (f->valid && f->has_time) {
		a->has_clock = true;
		a->clock_utc = f->utc;
		a->clock_ms = now_ms;
		if (a->prov.ok && slots_tick(&a->slots, f->utc, &out.ack)) {
			out.applied = true;
			acks_push(&a->acks, &out.ack);
		}
	}
	if (a->fence) {
		out.fenced = true;
		out.version = a->fence->version;
	}
	if (!f->valid || !a->fence) {
		return out;
	}

	struct geo_point p = {.lat = f->lat, .lon = f->lon};

	out.r = geofence_update(a->fence, p, f->accuracy_m);
	out.cmd = cue_update(&a->cue, &out.r, a->fence->cfg.warn_m, now_ms);
	return out;
}

/* Best effort for an ack when a command fails before its fields can be read */
static bool unverified_ack(const char *wire, size_t len, enum reject_code code,
			   struct slot_ack *ack)
{
	struct wire_scan sc;
	const struct wire_span *id, *ver;

	memset(ack, 0, sizeof(*ack));
	if (wire_scan(wire, len, &sc) != REJECT_NONE) {
		return false;
	}
	id = wire_find(wire, &sc, "command_id");
	ver = wire_find(wire, &sc, "version");
	if (!id || !ver || !wire_read_id(wire, id, false, NULL, &ack->command_id) ||
	    !wire_u32(wire + ver->val, ver->val_len, &ack->version)) {
		return false;
	}
	ack->status = ACK_REJECTED;
	ack->code = (uint8_t)code;
	return true;
}

enum reject_code app_boundary(struct app *a, const char *wire, size_t len, int64_t now_ms,
			      struct slot_ack *ack, bool *has_ack)
{
	enum reject_code code;
	int64_t now = 0;
	bool has_now;

	*has_ack = false;
	a->now_ms = now_ms;
	if (!a->prov.ok) {
		return REJECT_BAD_SIG; /* No server key to check it with */
	}

	has_now = app_now(a, now_ms, &now);
	code = command_parse(wire, len, a->prov.server_key, &a->cmd, a->e7, SHAPE_BUF_VERTICES);
	if (code != REJECT_NONE) {
		if (unverified_ack(wire, len, code, ack)) {
			ack->has_at = has_now;
			ack->at = has_now ? now : 0;
			acks_push(&a->acks, ack);
			*has_ack = true;
		}
		return code;
	}

	*ack = slots_insert(&a->slots, &a->cmd, has_now, now);
	acks_push(&a->acks, ack);
	*has_ack = true;
	return (enum reject_code)ack->code;
}

enum reject_code app_config(struct app *a, const char *wire, size_t len, int64_t now_ms)
{
	int64_t now = 0;
	bool has_now;
	enum reject_code code;

	a->now_ms = now_ms;
	if (!a->prov.ok) {
		return REJECT_BAD_SIG;
	}
	has_now = app_now(a, now_ms, &now);
	code = config_receive(&a->cfg, wire, len, a->prov.server_key, &a->prov.collar_id,
			      a->prov.endpoint, has_now, now);
	if (code == REJECT_NONE) {
		set_ids(a);
	}
	return code;
}

static void do_provision(struct app *a, const char *payload, size_t len, char *reply,
			 size_t cap)
{
	struct provision p;
	enum prov_error e = provision_parse(payload, len, &p);

	if (e != PROV_OK) {
		snprintf(reply, cap, "error %s", prov_error_str(e));
		return;
	}

	/* Wipe first: a power cut part way leaves the old provisioning with
	 * fewer slots, never the new provisioning with the old server's slots */
	slots_wipe(&a->slots);
	config_wipe(&a->cfg);
	acks_clear(&a->acks);
	a->fence = NULL;
	cue_rearm_at(&a->cue, a->now_ms);
	cue_set_mode(&a->cue, CUE_MODE_AUDIO);

	if (provision_save(payload, len) != 0) {
		snprintf(reply, cap, "error %s", prov_error_str(PROV_STORE_FAILED));
		set_ids(a);
		return;
	}
	a->prov = p;
	set_ids(a);
	snprintf(reply, cap, "ok %s", a->prov.collar_id.s);
}

static void do_status(struct app *a, char *reply, size_t cap)
{
	size_t n;
	const struct slot_hdr *act = slots_active(&a->slots);

	if (!a->prov.ok) {
		snprintf(reply, cap, "unprovisioned fw %s", APP_FW_VERSION);
		return;
	}

	const struct proto_id *herd = app_herd(a);

	n = (size_t)snprintf(reply, cap, "collar %s herd %s fw %s config ", a->prov.collar_id.s,
			     herd->s, APP_FW_VERSION);
	if (n < cap) {
		n += (size_t)(a->cfg.has ? snprintf(reply + n, cap - n, "%u", (unsigned)a->cfg.version)
					 : snprintf(reply + n, cap - n, "-"));
	}
	if (n < cap) {
		n += (size_t)(act ? snprintf(reply + n, cap - n, " active %u slots",
					     (unsigned)act->version)
				  : snprintf(reply + n, cap - n, " active - slots"));
	}
	for (int i = 0; i < a->slots.n && n < cap; i++) {
		n += (size_t)snprintf(reply + n, cap - n, " %u", (unsigned)a->slots.s[i].version);
	}
	if (a->slots.n == 0 && n < cap) {
		snprintf(reply + n, cap - n, " -");
	}
}

static void do_boundary(struct app *a, const char *wire, size_t len, bool overflow, char *reply,
			size_t cap)
{
	struct slot_ack ack;
	bool has_ack;
	enum reject_code code;

	if (!a->prov.ok) {
		snprintf(reply, cap, "error unprovisioned");
		return;
	}
	if (overflow) {
		snprintf(reply, cap, "error %s", reject_str(REJECT_TOO_LARGE));
		return;
	}
	code = app_boundary(a, wire, len, a->now_ms, &ack, &has_ack);
	if (!has_ack) {
		snprintf(reply, cap, "error %s", reject_str(code));
	} else if (ack.status == ACK_REJECTED) {
		snprintf(reply, cap, "rejected %u %s", (unsigned)ack.version, reject_str(ack.code));
	} else {
		snprintf(reply, cap, "%s %u", ack_status_str(ack.status), (unsigned)ack.version);
	}
}

static void do_config(struct app *a, const char *wire, size_t len, char *reply, size_t cap)
{
	enum reject_code code;

	if (!a->prov.ok) {
		snprintf(reply, cap, "error unprovisioned");
		return;
	}
	code = app_config(a, wire, len, a->now_ms);
	if (code != REJECT_NONE) {
		snprintf(reply, cap, "error %s", reject_str(code));
	} else {
		snprintf(reply, cap, "ok %u", (unsigned)a->cfg.version);
	}
}

/* `word` then a space (or the end of the line); *rest is what follows */
static bool command_is(const char *line, size_t len, const char *word, const char **rest,
		       size_t *rest_len)
{
	size_t n = strlen(word);

	if (len < n || memcmp(line, word, n) != 0 || (len > n && line[n] != ' ')) {
		return false;
	}
	*rest = line + n;
	*rest_len = len - n;
	while (*rest_len > 0 && **rest == ' ') {
		(*rest)++;
		(*rest_len)--;
	}
	return true;
}

void app_line(struct app *a, const char *line, size_t len, bool overflow, int64_t now_ms,
	      char *reply, size_t cap)
{
	const char *rest;
	size_t rest_len;

	a->now_ms = now_ms;
	reply[0] = '\0';

	/* Trim spaces around the line (terminals and scanners add them) */
	while (len > 0 && (line[0] == ' ' || line[0] == '\t')) {
		line++;
		len--;
	}
	while (len > 0 && (line[len - 1] == ' ' || line[len - 1] == '\t')) {
		len--;
	}
	if (len == 0) {
		return;
	}

	if (command_is(line, len, "boundary", &rest, &rest_len)) {
		do_boundary(a, rest, rest_len, overflow, reply, cap);
	} else if (overflow) {
		snprintf(reply, cap, "error too_long");
	} else if (command_is(line, len, "provision", &rest, &rest_len)) {
		do_provision(a, rest, rest_len, reply, cap);
	} else if (command_is(line, len, "status", &rest, &rest_len) && rest_len == 0) {
		do_status(a, reply, cap);
	} else if (command_is(line, len, "config", &rest, &rest_len)) {
		do_config(a, rest, rest_len, reply, cap);
	} else {
		snprintf(reply, cap, "error unknown_command");
	}
}
