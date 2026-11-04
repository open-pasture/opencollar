#include "rearm.h"

#include <string.h>

#include "command.h"

enum reject_code rearm_parse(const char *wire, size_t len, const uint8_t public_key[32],
			     struct rearm_cmd *out)
{
	struct wire_scan sc;
	enum reject_code code = wire_verify(wire, len, public_key, &sc);
	const struct wire_span *sp;
	char type_buf[16];
	size_t type_len;
	bool has;

	if (code != REJECT_NONE) {
		return code;
	}
	memset(out, 0, sizeof(*out));

	sp = wire_find(wire, &sc, OC_FIELD_TYPE);
	if (!sp || !wire_string(wire + sp->val, sp->val_len, type_buf, sizeof(type_buf) - 1,
				&type_len) ||
	    type_len != strlen(OC_TYPE_REARM) || memcmp(type_buf, OC_TYPE_REARM, type_len) != 0) {
		return REJECT_BAD_JSON;
	}

	if (!wire_read_id(wire, wire_find(wire, &sc, OC_FIELD_COMMAND_ID), false, NULL,
			  &out->command_id) ||
	    !wire_read_id(wire, wire_find(wire, &sc, OC_FIELD_COLLAR_ID), false, NULL,
			  &out->collar_id) ||
	    !wire_read_id(wire, wire_find(wire, &sc, OC_FIELD_HERD_ID), true, &out->has_herd,
			  &out->herd_id)) {
		return REJECT_BAD_JSON;
	}

	sp = wire_find(wire, &sc, OC_FIELD_REARM_SEQ);
	if (!sp || !wire_u32(wire + sp->val, sp->val_len, &out->rearm_seq)) {
		return REJECT_BAD_JSON;
	}

	if (!wire_read_time(wire, wire_find(wire, &sc, OC_FIELD_ISSUED_AT), &has, &out->issued_at) ||
	    !has ||
	    !wire_read_time(wire, wire_find(wire, &sc, OC_FIELD_EXPIRES_AT), &has,
			    &out->expires_at) ||
	    !has ||
	    !wire_read_time(wire, wire_find(wire, &sc, OC_FIELD_SHUTOFF_AT), &has,
			    &out->shutoff_at) ||
	    !has) {
		return REJECT_BAD_JSON;
	}

	sp = wire_find(wire, &sc, OC_FIELD_REASON_CODE);
	if (!sp || !wire_string(wire + sp->val, sp->val_len, out->reason_code, OC_REASON_CODE_MAX,
				&type_len) ||
	    type_len == 0 || type_len > OC_REASON_CODE_MAX) {
		return REJECT_BAD_JSON;
	}
	out->reason_code_len = (uint8_t)type_len;
	out->reason_code[type_len] = '\0';
	return REJECT_NONE;
}

enum reject_code rearm_check(const struct rearm_cmd *c, const struct proto_id *collar_id,
			     bool has_held_seq, uint32_t held_seq, bool enforcement_off,
			     bool has_shutoff_at, int64_t shutoff_at, bool has_now, int64_t now)
{
	if (!proto_id_eq(&c->collar_id, collar_id)) {
		return REJECT_WRONG_COLLAR;
	}
	/* Lifetime counter: refuse anything at or below the held seq. */
	if (has_held_seq && c->rearm_seq <= held_seq) {
		return REJECT_STALE;
	}
	if (!has_held_seq && c->rearm_seq == 0) {
		return REJECT_STALE; /* rearm_seq must be a positive monotonic counter */
	}
	/* shutoff_at must equal the persisted shut-off time exactly; also stale
	 * when enforcement is on. */
	if (!enforcement_off || !has_shutoff_at || c->shutoff_at != shutoff_at) {
		return REJECT_STALE;
	}
	/* No trusted time: accept (documented exception to not_now). */
	if (has_now && c->expires_at < now) {
		return REJECT_EXPIRED;
	}
	return REJECT_NONE;
}
