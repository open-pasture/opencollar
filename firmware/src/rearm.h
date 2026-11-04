/*
 * Signed rearm command (v1 JSON). Same Ed25519 / canonical-JSON path as
 * config. Field names live in wire_fields.h.
 *
 * Checks, in order after verify: ids (bad_json), wrong_collar, stale
 * (rearm_seq <= held, or shutoff_at mismatch / not shut off), expired
 * (expires_at earlier than trusted time). With no trusted time the collar
 * accepts an otherwise valid command (rearm_seq blocks replay; the server
 * expires undelivered ones) — see protocol/registry.md (not_now exception).
 */
#ifndef OPENCOLLAR_REARM_H
#define OPENCOLLAR_REARM_H

#include <stdbool.h>
#include <stdint.h>

#include "protocol.h"
#include "wire_fields.h"

struct rearm_cmd {
	struct proto_id command_id;
	struct proto_id collar_id;
	bool has_herd;
	struct proto_id herd_id;
	uint32_t rearm_seq;
	int64_t issued_at;
	int64_t expires_at;
	int64_t shutoff_at;
	char reason_code[OC_REASON_CODE_MAX + 1];
	uint8_t reason_code_len;
};

/* Scan, verify signature, read fields (too_large / bad_json / bad_sig). */
enum reject_code rearm_parse(const char *wire, size_t len, const uint8_t public_key[32],
			     struct rearm_cmd *out);

/*
 * wrong_collar, stale, expired.
 * has_held_seq / held_seq: persisted rearm_seq (0 and false = none yet).
 * enforcement_off / has_shutoff_at / shutoff_at: current persisted shut-off.
 * has_now / now: GNSS trusted time; if !has_now, expiry is not checked.
 */
enum reject_code rearm_check(const struct rearm_cmd *c, const struct proto_id *collar_id,
			     bool has_held_seq, uint32_t held_seq, bool enforcement_off,
			     bool has_shutoff_at, int64_t shutoff_at, bool has_now, int64_t now);

#endif
