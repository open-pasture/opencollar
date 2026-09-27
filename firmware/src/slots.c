#include "slots.h"

#include <string.h>

#include "store.h"

/* One record in flight: encode before a write, decode after a read */
static uint8_t rec_buf[SLOT_RECORD_MAX];

const char *ack_status_str(enum ack_status s)
{
	switch (s) {
	case ACK_RECEIVED:
		return "received";
	case ACK_APPLIED:
		return "applied";
	default:
		return "rejected";
	}
}

/* ---- Record encoding ---- */

static void put16(uint8_t *p, uint16_t v)
{
	p[0] = (uint8_t)v;
	p[1] = (uint8_t)(v >> 8);
}

static void put32(uint8_t *p, uint32_t v)
{
	for (int k = 0; k < 4; k++) {
		p[k] = (uint8_t)(v >> (8 * k));
	}
}

static void put64(uint8_t *p, uint64_t v)
{
	for (int k = 0; k < 8; k++) {
		p[k] = (uint8_t)(v >> (8 * k));
	}
}

static uint16_t get16(const uint8_t *p)
{
	return (uint16_t)(p[0] | p[1] << 8);
}

static uint32_t get32(const uint8_t *p)
{
	return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint64_t get64(const uint8_t *p)
{
	return (uint64_t)get32(p) | (uint64_t)get32(p + 4) << 32;
}

static uint32_t time32(int64_t t)
{
	return t < 0 ? 0 : (t > (int64_t)UINT32_MAX ? UINT32_MAX : (uint32_t)t);
}

static void put_double(uint8_t *p, double d)
{
	uint64_t u;

	memcpy(&u, &d, sizeof(u));
	put64(p, u);
}

static double get_double(const uint8_t *p)
{
	uint64_t u = get64(p);
	double d;

	memcpy(&d, &u, sizeof(d));
	return d;
}

uint32_t slot_encode(const struct slot_hdr *h, const int32_t (*v)[2], uint8_t *out)
{
	uint32_t len = slot_bytes(h);

	memset(out, 0, SLOT_HEADER_BYTES);
	put32(out + 0, SLOT_MAGIC);
	out[4] = SLOT_FORMAT;
	out[5] = h->flags;
	out[6] = (uint8_t)(h->rings - 1);
	out[7] = (uint8_t)h->ring_len[0];
	put16(out + 8, h->total);
	out[10] = h->command_id.len;
	out[11] = h->herd_id.len;
	put32(out + 12, h->version);
	put32(out + 16, time32(h->effective_at));
	put32(out + 20, time32(h->received_at));
	put32(out + 24, time32(h->applied_at));
	put_double(out + 28, h->warn_m);
	put_double(out + 36, h->hysteresis_m);
	for (int k = 1; k < h->rings; k++) {
		out[44 + k - 1] = (uint8_t)h->ring_len[k];
	}
	memcpy(out + 60, h->command_id.s, h->command_id.len);
	memcpy(out + 124, h->herd_id.s, h->herd_id.len);
	for (uint32_t i = 0; i < h->total; i++) {
		put32(out + SLOT_HEADER_BYTES + 8 * i, (uint32_t)v[i][0]);
		put32(out + SLOT_HEADER_BYTES + 8 * i + 4, (uint32_t)v[i][1]);
	}
	put32(out + 188, proto_crc32(0, out, len));
	return len;
}

bool slot_decode(const uint8_t *rec, uint32_t len, struct slot_hdr *h, int32_t (*v)[2])
{
	uint8_t crc[4];
	uint32_t want, got;

	if (len < SLOT_HEADER_BYTES || get32(rec) != SLOT_MAGIC || rec[4] != SLOT_FORMAT) {
		return false;
	}
	memset(h, 0, sizeof(*h));
	h->flags = rec[5];
	h->rings = (uint8_t)(rec[6] + 1);
	h->total = get16(rec + 8);
	if (h->rings > SHAPE_MAX_RINGS || h->total > SHAPE_MAX_TOTAL ||
	    len != limits_record_bytes(h->total) || rec[10] == 0 || rec[10] > PROTO_MAX_ID_BYTES ||
	    rec[11] > PROTO_MAX_ID_BYTES || (rec[11] == 0) != !(h->flags & SLOT_F_HERD)) {
		return false;
	}

	/* CRC over the record with its own field zeroed */
	memcpy(crc, rec + 188, 4);
	want = get32(crc);
	got = proto_crc32(0, rec, 188);
	got = proto_crc32(got, "\0\0\0\0", 4);
	got = proto_crc32(got, rec + 192, len - 192);
	if (got != want) {
		return false;
	}

	uint32_t sum = rec[7];

	h->ring_len[0] = rec[7];
	for (int k = 1; k < h->rings; k++) {
		h->ring_len[k] = rec[44 + k - 1];
		sum += h->ring_len[k];
	}
	for (int k = 0; k < h->rings; k++) {
		if (h->ring_len[k] < 3) {
			return false;
		}
	}
	if (sum != h->total) {
		return false;
	}
	/* A staged record always has its activation time */
	if (!(h->flags & SLOT_F_APPLIED) && !(h->flags & SLOT_F_EFFECTIVE)) {
		return false;
	}

	h->version = get32(rec + 12);
	h->effective_at = get32(rec + 16);
	h->received_at = get32(rec + 20);
	h->applied_at = get32(rec + 24);
	h->warn_m = get_double(rec + 28);
	h->hysteresis_m = get_double(rec + 36);
	proto_id_set(&h->command_id, (const char *)rec + 60, rec[10]);
	if (rec[11]) {
		proto_id_set(&h->herd_id, (const char *)rec + 124, rec[11]);
	}
	if (v) {
		for (uint32_t i = 0; i < h->total; i++) {
			v[i][0] = (int32_t)get32(rec + SLOT_HEADER_BYTES + 8 * i);
			v[i][1] = (int32_t)get32(rec + SLOT_HEADER_BYTES + 8 * i + 4);
		}
	}
	return true;
}

/* ---- State ---- */

void slots_init(struct slots *s, const struct collar_limits *limits, int32_t (*scratch)[2],
		slot_apply_fn apply, void *ctx)
{
	memset(s, 0, sizeof(*s));
	s->limits = *limits;
	if (s->limits.slots > SLOTS_MAX) {
		s->limits.slots = SLOTS_MAX;
	}
	s->warn_m = 5.0;
	s->hysteresis_m = 1.0;
	s->scratch = scratch;
	s->apply = apply;
	s->ctx = ctx;
}

void slots_set_collar(struct slots *s, const struct proto_id *collar)
{
	s->has_collar = collar != NULL;
	if (collar) {
		s->collar = *collar;
	}
}

static bool has_active(const struct slots *s)
{
	return s->n > 0 && (s->s[0].flags & SLOT_F_APPLIED);
}

const struct slot_hdr *slots_active(const struct slots *s)
{
	return has_active(s) ? &s->s[0] : NULL;
}

uint32_t slots_held(const struct slots *s)
{
	return s->n;
}

uint32_t slots_have(const struct slots *s)
{
	return s->n > 0 ? s->s[s->n - 1].version : 0;
}

uint32_t slots_free(const struct slots *s)
{
	return s->limits.slots > s->n ? s->limits.slots - s->n : 0;
}

static uint32_t used_bytes(const struct slots *s)
{
	uint32_t used = 0;

	for (int i = 0; i < s->n; i++) {
		used += slot_bytes(&s->s[i]);
	}
	return used;
}

bool slots_free_bytes(const struct slots *s, uint32_t *out)
{
	uint32_t used = used_bytes(s);

	if (s->limits.slot_bytes == 0) {
		return false;
	}
	*out = s->limits.slot_bytes > used ? s->limits.slot_bytes - used : 0;
	return true;
}

static void drop(struct slots *s, int i)
{
	if (store_delete(s->s[i].store_id) != 0) {
		s->store_errors++;
	}
	memmove(&s->s[i], &s->s[i + 1], (size_t)(s->n - i - 1) * sizeof(s->s[0]));
	s->n--;
}

/* Staged slots that insert would now refuse as wrong_herd go. The active one
 * stays in force until a boundary of this herd replaces it. */
static void drop_other_herds_staged(struct slots *s)
{
	int first = has_active(s) ? 1 : 0;

	if (!s->has_herd) {
		return;
	}
	for (int i = s->n - 1; i >= first; i--) {
		if ((s->s[i].flags & SLOT_F_HERD) && !proto_id_eq(&s->s[i].herd_id, &s->herd)) {
			drop(s, i);
		}
	}
}

void slots_set_herd(struct slots *s, const struct proto_id *herd)
{
	s->has_herd = herd != NULL;
	if (herd) {
		s->herd = *herd;
	}
	drop_other_herds_staged(s);
}

static uint16_t free_id(const struct slots *s)
{
	for (uint16_t id = STORE_ID_SLOT_BASE; id < STORE_ID_SLOT_BASE + SLOT_IDS; id++) {
		bool used = false;

		for (int i = 0; i < s->n; i++) {
			used |= s->s[i].store_id == id;
		}
		if (!used) {
			return id;
		}
	}
	return 0; /* Unreachable: one id more than the slots */
}

static bool persist(struct slots *s, const struct slot_hdr *h, const int32_t (*v)[2])
{
	uint32_t len = slot_encode(h, v, rec_buf);

	if (store_write(h->store_id, rec_buf, len) != 0) {
		s->store_errors++;
		return false;
	}
	return true;
}

/* Read a record back (header and vertices into scratch) */
static bool fetch(struct slots *s, const struct slot_hdr *want, struct slot_hdr *h)
{
	int len = store_read(want->store_id, rec_buf, sizeof(rec_buf));

	return len > 0 && len <= (int)sizeof(rec_buf) &&
	       slot_decode(rec_buf, (uint32_t)len, h, s->scratch) && h->version == want->version;
}

static struct slot_ack ack_of(const struct proto_id *id, uint32_t version, enum ack_status status,
			      enum reject_code code, bool has_at, int64_t at)
{
	struct slot_ack a = {
		.command_id = *id,
		.version = version,
		.status = (uint8_t)status,
		.code = (uint8_t)code,
		.has_at = has_at,
		.at = has_at ? at : 0,
	};

	return a;
}

static void header_from(const struct slots *s, const struct boundary_cmd *cmd,
			struct slot_hdr *h)
{
	memset(h, 0, sizeof(*h));
	h->version = cmd->version;
	h->rings = (uint8_t)cmd->shape.rings;
	for (int k = 0; k < h->rings; k++) {
		h->ring_len[k] = cmd->shape.len[k];
	}
	h->total = (uint16_t)cmd->shape.total;
	h->warn_m = cmd->has_warn ? cmd->warn_m : s->warn_m;
	h->hysteresis_m = cmd->has_hysteresis ? cmd->hysteresis_m : s->hysteresis_m;
	h->command_id = cmd->command_id;
	if (cmd->track) {
		h->flags |= SLOT_F_TRACK;
	}
	if (cmd->has_collar) {
		h->flags |= SLOT_F_COLLAR;
	}
	if (cmd->has_herd) {
		h->flags |= SLOT_F_HERD;
		h->herd_id = cmd->herd_id;
	}
	if (cmd->has_effective_at) {
		h->flags |= SLOT_F_EFFECTIVE;
		h->effective_at = cmd->effective_at;
	}
}

struct slot_ack slots_insert(struct slots *s, const struct boundary_cmd *cmd, bool has_now,
			     int64_t now)
{
	if (has_now) {
		s->clock = now;
		s->has_clock = true;
	}

#define REJECT(code) ack_of(&cmd->command_id, cmd->version, ACK_REJECTED, (code), has_now, now)

	if (cmd->has_herd && s->has_herd && !proto_id_eq(&cmd->herd_id, &s->herd)) {
		return REJECT(REJECT_WRONG_HERD);
	}
	if (cmd->has_collar && s->has_collar && !proto_id_eq(&cmd->collar_id, &s->collar)) {
		return REJECT(REJECT_WRONG_COLLAR);
	}
	for (int i = 0; i < s->n; i++) {
		const struct slot_hdr *h = &s->s[i];

		if (h->version != cmd->version) {
			continue;
		}
		if (h->flags & SLOT_F_APPLIED) {
			return ack_of(&h->command_id, h->version, ACK_APPLIED, REJECT_NONE,
				      h->flags & SLOT_F_APPLIED_AT, h->applied_at);
		}
		return ack_of(&h->command_id, h->version, ACK_RECEIVED, REJECT_NONE,
			      h->flags & SLOT_F_RECEIVED, h->received_at);
	}
	if (s->n > 0 && cmd->version < slots_have(s)) {
		return REJECT(REJECT_STALE);
	}

	double warn = cmd->has_warn ? cmd->warn_m : s->warn_m;
	double hyst = cmd->has_hysteresis ? cmd->hysteresis_m : s->hysteresis_m;
	enum reject_code code = shape_check(&cmd->shape, &s->limits, warn, hyst, 0.0);

	if (code != REJECT_NONE) {
		return REJECT(code);
	}

	struct slot_hdr h;
	uint32_t bytes = limits_record_bytes(cmd->shape.total);
	bool future = cmd->has_effective_at && (!s->has_clock || cmd->effective_at > s->clock);

	header_from(s, cmd, &h);
	if (has_now) {
		h.flags |= SLOT_F_RECEIVED;
		h.received_at = now;
	}

	if (!future) {
		if (s->limits.slot_bytes > 0 && bytes > s->limits.slot_bytes) {
			return REJECT(REJECT_SLOTS_FULL);
		}
		h.flags |= SLOT_F_APPLIED;
		if (has_now) {
			h.flags |= SLOT_F_APPLIED_AT;
			h.applied_at = now;
		}
		h.store_id = free_id(s);

		/* Enforce first, then persist, then drop every lower version */
		if (s->apply) {
			s->apply(s->ctx, &h, (const int32_t(*)[2])cmd->shape.v);
		}
		if (persist(s, &h, (const int32_t(*)[2])cmd->shape.v)) {
			while (s->n > 0) {
				drop(s, s->n - 1);
			}
		} else {
			/* Enforced but not stored: keep the old records so a reboot
			 * comes back to a fence that is on flash */
			s->n = 0;
		}
		s->s[0] = h;
		s->n = 1;
		return ack_of(&h.command_id, h.version, ACK_APPLIED, REJECT_NONE, has_now, now);
	}

	/* Staged. The new version is the highest, so any staged one activating
	 * at or after it is dead. */
	int first = has_active(s) ? 1 : 0;
	uint32_t count = (uint32_t)first + 1;
	uint32_t used = (first ? slot_bytes(&s->s[0]) : 0) + bytes;

	for (int i = first; i < s->n; i++) {
		if (s->s[i].effective_at < cmd->effective_at) {
			count++;
			used += slot_bytes(&s->s[i]);
		}
	}
	if (count > s->limits.slots || (s->limits.slot_bytes > 0 && used > s->limits.slot_bytes)) {
		return REJECT(REJECT_SLOTS_FULL);
	}

	h.store_id = free_id(s);
	if (!persist(s, &h, (const int32_t(*)[2])cmd->shape.v)) {
		/* Couldn't store it: no room, as far as the server is concerned */
		return REJECT(REJECT_SLOTS_FULL);
	}
	for (int i = s->n - 1; i >= first; i--) {
		if (s->s[i].effective_at >= cmd->effective_at) {
			drop(s, i);
		}
	}
	s->s[s->n++] = h;
	return ack_of(&h.command_id, h.version, ACK_RECEIVED, REJECT_NONE, has_now, now);
#undef REJECT
}

bool slots_tick(struct slots *s, int64_t now, struct slot_ack *ack)
{
	s->clock = now;
	s->has_clock = true;

	for (;;) {
		int first = has_active(s) ? 1 : 0;
		int k = -1;
		struct slot_hdr h;

		for (int i = first; i < s->n; i++) {
			if (s->s[i].effective_at <= now) {
				k = i;
			}
		}
		if (k < 0) {
			return false;
		}
		if (!fetch(s, &s->s[k], &h)) {
			/* Unreadable: it can't be enforced, so it goes */
			drop(s, k);
			continue;
		}
		h.store_id = s->s[k].store_id;
		h.flags |= SLOT_F_APPLIED | SLOT_F_APPLIED_AT;
		h.applied_at = now;

		if (s->apply) {
			s->apply(s->ctx, &h, (const int32_t(*)[2])s->scratch);
		}
		persist(s, &h, (const int32_t(*)[2])s->scratch);
		s->s[k] = h;
		while (k > 0) {
			drop(s, --k);
		}
		*ack = ack_of(&h.command_id, h.version, ACK_APPLIED, REJECT_NONE, true, now);
		return true;
	}
}

void slots_load(struct slots *s)
{
	struct slot_hdr h;

	s->n = 0;
	s->has_clock = false;

	for (uint16_t id = STORE_ID_SLOT_BASE; id < STORE_ID_SLOT_BASE + SLOT_IDS; id++) {
		int len = store_read(id, rec_buf, sizeof(rec_buf));

		if (len <= 0 || len > (int)sizeof(rec_buf) ||
		    !slot_decode(rec_buf, (uint32_t)len, &h, NULL)) {
			continue; /* Absent, or a bad format or CRC: ignored */
		}
		h.store_id = id;

		int i = s->n++;

		while (i > 0 && s->s[i - 1].version > h.version) {
			s->s[i] = s->s[i - 1];
			i--;
		}
		s->s[i] = h;
	}

	/* Duplicate versions (never written, but tidy): keep the applied one */
	for (int i = 1; i < s->n;) {
		if (s->s[i].version == s->s[i - 1].version) {
			drop(s, (s->s[i].flags & SLOT_F_APPLIED) ? i - 1 : i);
		} else {
			i++;
		}
	}

	/* The highest applied record is the active one; everything below it goes */
	int a = -1;

	for (int i = 0; i < s->n; i++) {
		if (s->s[i].flags & SLOT_F_APPLIED) {
			a = i;
		}
	}
	while (a > 0) {
		drop(s, 0);
		a--;
	}
	for (int i = 1; i < s->n; i++) {
		s->s[i].flags &= (uint8_t)~SLOT_F_APPLIED;
	}

	/* Another herd's staged slots (a power cut after a herd change's config
	 * was stored, before they were deleted) */
	drop_other_herds_staged(s);

	/* Dead staged slots (a power cut before they were pruned) */
	int first = has_active(s) ? 1 : 0;

	for (int i = s->n - 1; i >= first; i--) {
		for (int j = i + 1; j < s->n; j++) {
			if (s->s[j].effective_at <= s->s[i].effective_at) {
				drop(s, i);
				break;
			}
		}
	}

	/* Over the limits (only if they shrank between builds): drop the newest staged */
	while (s->n > first &&
	       (s->n > s->limits.slots ||
		(s->limits.slot_bytes > 0 && used_bytes(s) > s->limits.slot_bytes))) {
		drop(s, s->n - 1);
	}

	if (has_active(s)) {
		if (fetch(s, &s->s[0], &h)) {
			h.store_id = s->s[0].store_id;
			s->s[0] = h;
			if (s->apply) {
				s->apply(s->ctx, &s->s[0], (const int32_t(*)[2])s->scratch);
			}
		} else {
			drop(s, 0);
		}
	}
}

void slots_wipe(struct slots *s)
{
	for (uint16_t id = STORE_ID_SLOT_BASE; id < STORE_ID_SLOT_BASE + SLOT_IDS; id++) {
		if (store_delete(id) != 0) {
			s->store_errors++;
		}
	}
	s->n = 0;
}
