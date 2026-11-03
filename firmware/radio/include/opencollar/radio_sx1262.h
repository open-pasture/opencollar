/*
 * SX1262 backend for opencollar/radio_hal.h (firmware/lora).
 *
 * Defines struct oc_radio for the hardware path and open/close helpers.
 * Portable callers only include opencollar/radio_hal.h.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RADIO_SX1262_H
#define OPENCOLLAR_RADIO_SX1262_H

#include "opencollar/radio_hal.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define OC_RADIO_MTU 255u

/* US915 bring-up defaults (125 kHz, SF8, CR 4/5). See docs/FCC-US915.md. */
#define OC_RADIO_US915_FREQ_HZ          903900000u
#define OC_RADIO_US915_SF_DEFAULT       8u
#define OC_RADIO_US915_BW_CODE_125K     0u
#define OC_RADIO_US915_CR_4_5           5u
#define OC_RADIO_US915_TX_CAP_DBM       14
#define OC_RADIO_US915_DUTY_WINDOW_US   (3600u * 1000000u)
#define OC_RADIO_US915_DUTY_LIMIT_US    (36000000u) /* ~1 % of an hour */
#define OC_RADIO_US915_DWELL_LIMIT_US   400000u
#define OC_RADIO_US915_DWELL_WINDOW_MS  20000u
#define OC_RADIO_US915_MIN_TX_GAP_MS    100u
#define OC_RADIO_US915_MAX_FRAME_AIR_US 400000u

typedef struct oc_radio_hw_ops {
	oc_radio_status_t (*cad)(void *ctx, oc_radio_cad_result_t *out);
	oc_radio_status_t (*send)(void *ctx, const uint8_t *buf, size_t len,
				  int8_t dbm);
	oc_radio_status_t (*recv)(void *ctx, uint8_t *buf, size_t cap,
				  size_t *out_len, oc_radio_rx_meta_t *meta,
				  uint32_t timeout_ms);
	oc_radio_status_t (*set_power)(void *ctx, int8_t dbm);
	oc_radio_status_t (*sleep)(void *ctx); /* optional; NULL ok */
	uint32_t (*now_ms)(void *ctx);
	uint32_t (*rand32)(void *ctx);
	void *ctx;
} oc_radio_hw_ops_t;

typedef struct oc_radio_cfg {
	uint32_t freq_hz;
	uint8_t sf;            /* 7..10 bring-up */
	uint8_t bw_khz_code;   /* 0=125, 1=250, 2=500 */
	uint8_t cr;            /* 5..8 */
	uint8_t preamble;
	uint8_t sync_word;
	int8_t tx_power_dbm;
	int8_t tx_power_cap_dbm;
	uint32_t mtu;
	uint32_t duty_window_us;
	uint32_t duty_limit_us;
	uint32_t dwell_limit_us;
	uint32_t dwell_window_ms;
	uint16_t min_tx_gap_ms;
	uint32_t max_frame_airtime_us;
	bool cad_before_tx;
} oc_radio_cfg_t;

struct oc_radio {
	oc_radio_cfg_t cfg;
	oc_radio_hw_ops_t ops;
	void *hw; /* backend-private (e.g. Zephyr device *) */
	int8_t power_dbm;
	uint32_t duty_used_us;
	uint32_t duty_window_start_ms;
	uint32_t dwell_used_us;
	uint32_t dwell_window_start_ms;
	uint32_t dwell_freq_hz;
	uint32_t last_tx_end_ms;
	uint64_t rng;
	bool inited;
};

void oc_radio_cfg_us915_defaults(oc_radio_cfg_t *cfg);

/*
 * Bind a radio handle to hardware (or mock) ops. Does not touch the SX1262
 * until the first send/recv/cad (ops may init lazily).
 */
oc_radio_status_t oc_radio_sx1262_open(oc_radio_t *radio,
				       const oc_radio_cfg_t *cfg,
				       const oc_radio_hw_ops_t *ops);

void oc_radio_sx1262_close(oc_radio_t *radio);

/* Radio-local until radio_hal.h gains sleep/now (flagged for op-fw-proto). */
oc_radio_status_t oc_radio_sx1262_sleep(oc_radio_t *radio);
uint32_t oc_radio_sx1262_now_ms(const oc_radio_t *radio);

/* Host-test / mock binder (tests/host). */
void oc_radio_mock_reset(void);
void oc_radio_mock_ops(oc_radio_hw_ops_t *ops);
void oc_radio_mock_set_time_ms(uint32_t ms);
void oc_radio_mock_advance_ms(uint32_t ms);
void oc_radio_mock_set_cad_busy(int busy);
void oc_radio_mock_queue_rx(const uint8_t *buf, size_t len, int16_t rssi,
			    int8_t snr);
uint32_t oc_radio_mock_tx_count(void);

#ifdef __ZEPHYR__
struct device;
oc_radio_status_t oc_radio_zephyr_ops(oc_radio_hw_ops_t *ops,
				      const struct device *dev);
oc_radio_status_t oc_radio_sx1262_open_zephyr(oc_radio_t *radio,
					      const oc_radio_cfg_t *cfg,
					      const struct device *dev);
#endif

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_RADIO_SX1262_H */
