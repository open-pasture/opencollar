/*
 * Host mock backend controls (tests only).
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RHAL_MOCK_H
#define OPENCOLLAR_RHAL_MOCK_H

#include "radio_hal.h"

void rhal_mock_reset(void);
void rhal_mock_platform(struct rhal_platform *plat);
void rhal_mock_set_time_us(uint64_t t);
void rhal_mock_advance_us(uint64_t dt);
void rhal_mock_set_cad_busy(int busy);
void rhal_mock_queue_rx(const uint8_t *buf, uint8_t len, int16_t rssi, int8_t snr);
uint32_t rhal_mock_tx_count(void);
const uint8_t *rhal_mock_last_tx(uint8_t *len_out);

#endif
