/* SPDX-License-Identifier: Apache-2.0 */
/*
 * STUB, not used yet. The Starling roster a Rook will carry upstream once
 * the LoRa side exists: which Starlings it heard, how fresh, and which fence
 * they hold. Reports reserve the key "roster" for its summary; v1 reports
 * never send it today. Names here are placeholders, not v2 identifiers.
 */
#ifndef ROOK_ROSTER_H
#define ROOK_ROSTER_H

#include <stdint.h>

#define ROOK_ROSTER_MAX 32

struct rook_roster_entry {
	uint16_t short_addr;      /* placeholder for the v2 short address */
	int64_t last_heard;       /* GNSS UTC, Unix seconds */
	uint32_t fence_seq;       /* Highest fence the Starling reported holding */
	int8_t rssi_dbm;
	int8_t snr_db;
	uint8_t battery_pct;      /* 0xff unknown */
};

struct rook_roster {
	uint16_t n;
	struct rook_roster_entry e[ROOK_ROSTER_MAX];
};

/* Freshness summary that would go upstream (reserved report key "roster") */
struct rook_roster_summary {
	uint16_t heard;        /* Starlings heard in the window */
	uint16_t stale;        /* Holding a fence_seq below the Rook's */
	int64_t oldest_heard;  /* Oldest last_heard among them */
};

#endif
