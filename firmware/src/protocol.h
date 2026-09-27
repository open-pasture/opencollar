/*
 * Protocol v1 building blocks shared by the command, config, slot and
 * provisioning code: rejection codes, collar limits, ids, times, CRC-32 and
 * base64. Plain C, no Zephyr dependencies, so it runs in host tests.
 *
 * The protocol itself is in protocol/README.md.
 */
#ifndef OPENCOLLAR_PROTOCOL_H
#define OPENCOLLAR_PROTOCOL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Largest command the collar accepts, bytes of wire text */
#define PROTO_MAX_COMMAND_BYTES 12288
/* Most top-level keys in a command */
#define PROTO_MAX_KEYS 16
/* Longest command_id, herd_id or collar_id, bytes */
#define PROTO_MAX_ID_BYTES 64
/* Longest endpoint URL, bytes */
#define PROTO_MAX_ENDPOINT_BYTES 256

/* Why a command was rejected: the ack's `code`. Every code but slots_full is permanent. */
enum reject_code {
	REJECT_NONE = 0,
	REJECT_BAD_SIG,
	REJECT_WRONG_HERD,
	REJECT_WRONG_COLLAR,
	REJECT_BAD_JSON,
	REJECT_TOO_LARGE,
	REJECT_STALE,
	REJECT_OUT_OF_RANGE,
	REJECT_TOO_FEW_VERTICES,
	REJECT_TOO_MANY_VERTICES,
	REJECT_TOO_MANY_HOLES,
	REJECT_SELF_INTERSECTING,
	REJECT_RINGS_CROSS,
	REJECT_HOLE_OUTSIDE,
	REJECT_HOLES_OVERLAP,
	REJECT_ZERO_AREA,
	REJECT_HOLE_TOO_SMALL,
	REJECT_HOLE_TOO_CLOSE,
	REJECT_BAD_MARGINS,
	REJECT_SLOTS_FULL,
	REJECT_BAD_CONFIG,
	REJECT_COUNT,
};

/* "bad_sig" etc.; "" for REJECT_NONE */
const char *reject_str(enum reject_code code);
/* REJECT_NONE when the text is not a code */
enum reject_code reject_parse(const char *s);

/* What a collar holds (protocol v1 §3.1). slot_bytes 0 = no byte cap known. */
struct collar_limits {
	uint16_t outer;
	uint16_t holes;
	uint16_t hole_vertices;
	uint16_t total;
	uint16_t slots;
	uint32_t slot_bytes;
};

extern const struct collar_limits LIMITS_LEGACY;
extern const struct collar_limits LIMITS_V0;
extern const struct collar_limits LIMITS_V1;

/* Flash bytes of one slot record: 192-byte header + 8 bytes per vertex */
static inline uint32_t limits_record_bytes(uint32_t total_vertices)
{
	return 192u + 8u * total_vertices;
}

/* An id of 1-64 bytes, NUL-terminated for printing */
struct proto_id {
	uint8_t len;
	char s[PROTO_MAX_ID_BYTES + 1];
};

bool proto_id_eq(const struct proto_id *a, const struct proto_id *b);
/* Copies up to 64 bytes; returns false (and an empty id) when len is 0 or > 64 */
bool proto_id_set(struct proto_id *id, const char *s, size_t len);

/*
 * RFC 3339 time to Unix seconds (fractions dropped). Accepts `Z` or a
 * numeric offset. Returns false when the text is not a valid time.
 */
bool proto_time_parse(const char *s, size_t len, int64_t *out);
/* A UTC calendar time (GNSS date and time) to Unix seconds */
int64_t proto_time_civil(int year, int month, int day, int hour, int minute, int second);
/* Unix seconds as "2026-09-27T12:00:00Z" (needs 21 bytes incl. NUL). Returns the length. */
int proto_time_format(int64_t t, char *out, size_t cap);

/* CRC-32 (IEEE 802.3), continue from a previous value (start with 0) */
uint32_t proto_crc32(uint32_t crc, const void *data, size_t len);

/*
 * Standard base64 with padding, strict: the length must be a multiple of 4,
 * padding canonical and unused bits zero. Returns the decoded length, or -1.
 */
int proto_base64_decode(const char *in, size_t len, uint8_t *out, size_t cap);

#endif
