/*
 * LoRa airtime (Semtech AN1200.13) for the US915 bring-up preset.
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RADIO_AIRTIME_H
#define OPENCOLLAR_RADIO_AIRTIME_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

struct radio_airtime_params {
	uint32_t bandwidth_hz;     /* e.g. 125000 */
	uint8_t spreading_factor;    /* 7..12 */
	uint8_t coding_rate;       /* 5..8 meaning 4/5 .. 4/8 */
	uint8_t preamble_symbols;  /* typically 8 */
	bool explicit_header;
	bool crc_on;
	bool low_data_rate;        /* force LDR optimize; else auto for Tsym > 16 ms */
};

/* Symbol duration in microseconds. */
uint32_t radio_airtime_tsym_us(uint8_t sf, uint32_t bandwidth_hz);

/* Full packet airtime in microseconds for payload_len bytes. */
uint32_t radio_airtime_packet_us(const struct radio_airtime_params *p,
				 size_t payload_len);

#endif
