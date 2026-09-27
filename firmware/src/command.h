/*
 * Signed commands as the collar receives them (protocol v1 §3.2, §3.4).
 * Plain C, host-testable.
 *
 * The collar doesn't build a JSON tree. It scans the raw text once, records
 * up to 16 top-level key/value spans, sorts them by key bytes and streams the
 * canonical form (keys sorted, `sig` left out, value tokens copied verbatim
 * with whitespace outside strings removed) into SHA-512 to check the Ed25519
 * signature (Monocypher). Only then are the fields read, straight from the
 * spans: coordinates are converted to e7 integers exactly, with no float
 * round trip.
 *
 * Checked in this order, as openpasture's op_protocol::verify_wire:
 *  1. too_large  more than 12 288 bytes
 *  2. bad_json   not UTF-8; not one JSON object; a nested object anywhere;
 *                arrays deeper than 4; a key with a backslash; a duplicate
 *                key; more than 16 keys; anything after the object
 *  3. bad_sig    no `sig`, `sig` not a plain base64 string of 64 bytes, or a
 *                signature that doesn't verify
 *  4. bad_json   the fields don't make a command (types, required fields,
 *                ids empty or over 64 bytes). Unknown keys are signed and ignored.
 *
 * Ed25519 runs on the caller's stack: call this from the main thread (8 KB
 * stack), never from the system workqueue.
 */
#ifndef OPENCOLLAR_COMMAND_H
#define OPENCOLLAR_COMMAND_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "protocol.h"
#include "shape.h"

/* ---- The top-level span scanner, shared with config and provisioning ---- */

struct wire_span {
	uint16_t key, key_len; /* The key's bytes, without quotes */
	uint16_t val, val_len; /* The value token as sent */
};

struct wire_scan {
	struct wire_span span[PROTO_MAX_KEYS];
	uint8_t n;
	int8_t sig; /* Index of the `sig` span, or -1 */
};

/* Size, UTF-8 and the span scan: REJECT_NONE, REJECT_TOO_LARGE or REJECT_BAD_JSON */
enum reject_code wire_scan(const char *w, size_t len, struct wire_scan *out);

/* The canonical bytes, in pieces */
typedef void (*wire_sink)(void *ctx, const uint8_t *p, size_t n);
void wire_canonical(const char *w, const struct wire_scan *sc, wire_sink sink, void *ctx);

/* wire_scan, then the Ed25519 signature over the canonical bytes */
enum reject_code wire_verify(const char *w, size_t len, const uint8_t public_key[32],
			     struct wire_scan *out);

/* The span for a key, or NULL */
const struct wire_span *wire_find(const char *w, const struct wire_scan *sc, const char *key);

/* ---- Value tokens ---- */

bool wire_is_null(const char *t, size_t n);
/* A JSON string: decoded into out (up to cap bytes, not NUL-terminated);
 * *len is the full decoded length even when it is over cap. */
bool wire_string(const char *t, size_t n, char *out, size_t cap, size_t *len);
/* An integer 0..4294967295 (no fraction, no exponent) */
bool wire_u32(const char *t, size_t n, uint32_t *out);
/* Any JSON number that fits a double */
bool wire_f64(const char *t, size_t n, double *out);
/*
 * Degrees x 1e7, rounded half away from zero, computed exactly from the
 * decimal text. *in_range: |value| <= limit_e7 exactly. False when the token
 * is not a number or doesn't fit a double.
 */
bool wire_e7(const char *t, size_t n, int64_t limit_e7, int64_t *e7, bool *in_range);

/* An id of 1-64 bytes. Optional: absent or null gives *has = false. */
bool wire_read_id(const char *w, const struct wire_span *sp, bool optional, bool *has,
		  struct proto_id *id);
/* An optional RFC 3339 time: absent or null gives *has = false. */
bool wire_read_time(const char *w, const struct wire_span *sp, bool *has, int64_t *t);

/* ---- Boundary command ---- */

struct boundary_cmd {
	struct proto_id command_id;
	bool has_herd;
	struct proto_id herd_id;
	bool has_collar;
	struct proto_id collar_id;
	uint32_t version;
	bool has_effective_at;
	int64_t effective_at; /* Unix seconds */
	bool track;           /* cue_mode "track"; "audio" is the default */
	bool has_warn;
	double warn_m;
	bool has_hysteresis;
	double hysteresis_m;
	struct shape shape; /* Outer ring then holes, e7, cleaned */
};

/*
 * Scan, verify and read a boundary command. Vertices go into buf (cap
 * vertices; SHAPE_BUF_VERTICES holds any valid command). Herd, collar,
 * version and shape rules are the slot store's (slots_insert).
 */
enum reject_code command_parse(const char *wire, size_t len, const uint8_t public_key[32],
			       struct boundary_cmd *cmd, int32_t (*buf)[2], uint16_t cap);

#endif
