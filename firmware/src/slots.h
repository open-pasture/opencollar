/*
 * Slots: the boundaries a collar holds (protocol v1 §3.7). Plain C, time
 * passed in, persistence through store.h, so it runs in host tests.
 *
 * - The boundary in effect at time t is the highest version whose activation
 *   time (effective_at, else the time it was received) is at or before t. A
 *   staged version is dead when a higher version activates at or before it.
 * - Only versions above every version held are accepted (anti-replay). A
 *   version equal to one held is re-acked with that version's current
 *   status; a lower one is `stale`.
 * - Immediate (no effective_at, or it has passed on the GNSS clock):
 *   validate, swap into the fence (the apply callback, which also rearms the
 *   cue), persist, drop every lower version, ack `applied`.
 * - Future: persist as staged, prune dead slots, ack `received`. No free slot,
 *   or not enough slot bytes after pruning, is `slots_full`.
 * - Tick on every fix with that fix's GNSS time, the only clock for
 *   activation: the highest due version applies, lower ones go (superseded
 *   staged slots get no ack), acked `applied` at the fix's time.
 * - Boot: load the records, check format and CRC, enforce the latest active
 *   boundary at once (no clock needed); staged slots wait for the first fix.
 * - Herd change (a signed config naming another herd): staged slots of any
 *   other herd go, with no ack (the next report's slots and a lower `have`
 *   show it); the active boundary stays in force until one of the new herd
 *   applies. Boot drops them too, for a power cut between the config write
 *   and the deletes. Slots without a herd_id stay, as insert takes them.
 *
 * Checks on insert, in order: wrong_herd, wrong_collar, re-ack or stale, the
 * shape rules, slots_full (ids and fields were checked by command_parse).
 * This is the logic of openpasture's op_protocol::SlotStore.
 *
 * Record (NVS id 0x100 + i): a 192-byte header, then 8 bytes per vertex
 * (int32 lon, lat x 1e7, little-endian), outer ring first. Header:
 *   0 magic "OCS1"   4 format (1)   5 flags   6 holes   7 outer vertices
 *   8 total vertices (u16)   10 command_id length   11 herd_id length
 *  12 version   16 effective_at   20 received_at   24 applied_at (u32 Unix s)
 *  28 warn_m   36 hysteresis_m (f64)   44 hole lengths[16]
 *  60 command_id[64]   124 herd_id[64]   188 CRC-32 of the record (this field 0)
 * One id more than the slot count exists, so a new record is always written
 * before the ones it replaces are deleted: a power cut leaves the old set or
 * the new one, and boot tidies up whatever is left over.
 */
#ifndef OPENCOLLAR_SLOTS_H
#define OPENCOLLAR_SLOTS_H

#include <stdbool.h>
#include <stdint.h>

#include "command.h"
#include "protocol.h"
#include "shape.h"

#ifdef CONFIG_OPENCOLLAR_SLOTS
#define SLOTS_MAX CONFIG_OPENCOLLAR_SLOTS
#else
#define SLOTS_MAX 16
#endif

#define SLOT_IDS (SLOTS_MAX + 1)
#define SLOT_HEADER_BYTES 192
#define SLOT_RECORD_MAX (SLOT_HEADER_BYTES + 8 * SHAPE_MAX_TOTAL)
#define SLOT_MAGIC 0x3153434fu /* "OCS1" */
#define SLOT_FORMAT 1

#define SLOT_F_APPLIED 0x01    /* The active boundary */
#define SLOT_F_TRACK 0x02      /* cue_mode track */
#define SLOT_F_COLLAR 0x04     /* A collar-scoped command (collar_id matched ours) */
#define SLOT_F_HERD 0x08       /* herd_id present */
#define SLOT_F_EFFECTIVE 0x10  /* effective_at present */
#define SLOT_F_RECEIVED 0x20   /* received_at known (GNSS time) */
#define SLOT_F_APPLIED_AT 0x40 /* applied_at known (GNSS time) */

enum ack_status {
	ACK_RECEIVED = 0,
	ACK_APPLIED,
	ACK_REJECTED,
};

const char *ack_status_str(enum ack_status s);

/* What to acknowledge. at is GNSS time when the collar had one; the sender
 * fills a missing one (modem network time). */
struct slot_ack {
	struct proto_id command_id;
	uint32_t version;
	uint8_t status; /* enum ack_status */
	uint8_t code;   /* enum reject_code */
	bool has_at;
	int64_t at;
};

struct slot_hdr {
	uint32_t version;
	uint8_t flags;
	uint8_t rings; /* 1 + holes */
	uint16_t ring_len[SHAPE_MAX_RINGS];
	uint16_t total;
	int64_t effective_at, received_at, applied_at; /* Unix s, per flags */
	double warn_m, hysteresis_m;
	struct proto_id command_id;
	struct proto_id herd_id;
	uint16_t store_id;
};

static inline uint32_t slot_bytes(const struct slot_hdr *h)
{
	return limits_record_bytes(h->total);
}

/* The active boundary changed: build the fence from these rings and rearm the cue. */
typedef void (*slot_apply_fn)(void *ctx, const struct slot_hdr *hdr, const int32_t (*v)[2]);

struct slots {
	struct collar_limits limits;
	bool has_herd;
	struct proto_id herd;
	bool has_collar;
	struct proto_id collar;
	double warn_m, hysteresis_m; /* For commands without margins */
	struct slot_hdr s[SLOT_IDS]; /* Ascending version; s[0] is active when flagged */
	uint8_t n;
	bool has_clock;
	int64_t clock; /* Last GNSS time since boot */
	int32_t (*scratch)[2]; /* SHAPE_BUF_VERTICES, for records read back */
	slot_apply_fn apply;
	void *ctx;
	uint32_t store_errors; /* Writes or deletes that failed */
};

void slots_init(struct slots *s, const struct collar_limits *limits, int32_t (*scratch)[2],
		slot_apply_fn apply, void *ctx);
/* The herd wrong_herd is checked against; staged slots of another herd go
 * (from flash too). NULL: unknown, the check is skipped and nothing goes. */
void slots_set_herd(struct slots *s, const struct proto_id *herd);
void slots_set_collar(struct slots *s, const struct proto_id *collar);

/* Boot: load and tidy the records, apply the active one. The clock is gone.
 * Set the herd first: another herd's staged records are dropped. */
void slots_load(struct slots *s);

/* Offer a command whose signature verified. has_now: the collar's GNSS time
 * now; without it, the last fix's time since boot decides whether a staged
 * boundary is already due. */
struct slot_ack slots_insert(struct slots *s, const struct boundary_cmd *cmd, bool has_now,
			     int64_t now);

/* A fix at GNSS time now: apply the highest staged version that is due. */
bool slots_tick(struct slots *s, int64_t now, struct slot_ack *ack);

/* Provisioning: forget every slot. */
void slots_wipe(struct slots *s);

const struct slot_hdr *slots_active(const struct slots *s);
uint32_t slots_held(const struct slots *s);
/* Highest version held, applied or staged; 0 with none (`have=`) */
uint32_t slots_have(const struct slots *s);
/* Slots left (`free=`) */
uint32_t slots_free(const struct slots *s);
/* Slot bytes left (`free_bytes=`); false when the limits have no byte cap */
bool slots_free_bytes(const struct slots *s, uint32_t *out);

/* Record encoding, exposed for tests. encode returns the record size. */
uint32_t slot_encode(const struct slot_hdr *h, const int32_t (*v)[2], uint8_t *out);
bool slot_decode(const uint8_t *rec, uint32_t len, struct slot_hdr *h, int32_t (*v)[2]);

#endif
