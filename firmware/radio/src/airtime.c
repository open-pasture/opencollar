/*
 * Semtech AN1200.13 LoRa packet airtime.
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_airtime.h"

#include <stddef.h>

uint32_t radio_airtime_tsym_us(uint8_t sf, uint32_t bandwidth_hz)
{
	if (sf < 5u || sf > 12u || bandwidth_hz == 0u) {
		return 0u;
	}
	/* Tsym = 2^SF / BW seconds → microseconds */
	return (uint32_t)(((uint64_t)(1u << sf) * 1000000ull) / bandwidth_hz);
}

uint32_t radio_airtime_packet_us(const struct radio_airtime_params *p,
				 size_t payload_len)
{
	uint32_t tsym;
	uint32_t t_preamble;
	int32_t payload_symb_nb;
	uint32_t t_payload;
	uint8_t cr;
	bool de;
	int32_t num;
	int32_t den;

	if (p == NULL || p->spreading_factor < 5u || p->spreading_factor > 12u ||
	    p->bandwidth_hz == 0u || p->coding_rate < 5u || p->coding_rate > 8u) {
		return 0u;
	}

	tsym = radio_airtime_tsym_us(p->spreading_factor, p->bandwidth_hz);
	if (tsym == 0u) {
		return 0u;
	}

	/* LDR optimize when symbol time > 16 ms, unless overridden. */
	de = p->low_data_rate || (tsym > 16000u);

	cr = (uint8_t)(p->coding_rate - 4u); /* CR in formula is 1..4 */

	/*
	 * payloadSymbNb = 8 + max(ceil((8PL - 4SF + 28 + 16CRC - 20IH)/(4(SF - 2DE))) * (CR+4), 0)
	 * IH = 0 for explicit header, 1 for implicit.
	 */
	num = (int32_t)(8 * (int32_t)payload_len - 4 * (int32_t)p->spreading_factor + 28 +
			(p->crc_on ? 16 : 0) - (p->explicit_header ? 0 : 20));
	den = 4 * ((int32_t)p->spreading_factor - (de ? 2 : 0));
	if (den <= 0) {
		return 0u;
	}
	if (num < 0) {
		payload_symb_nb = 8;
	} else {
		payload_symb_nb = 8 + ((num + den - 1) / den) * (int32_t)(cr + 4u);
	}

	/* Preamble duration = (Npreamble + 4.25) * Tsym */
	t_preamble = (uint32_t)((p->preamble_symbols * tsym) + (tsym * 17u) / 4u);
	t_payload = (uint32_t)payload_symb_nb * tsym;
	return t_preamble + t_payload;
}
