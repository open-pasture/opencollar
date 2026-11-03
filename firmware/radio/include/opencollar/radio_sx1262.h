/*
 * SX1262 backend for opencollar/radio_hal.h (firmware/lora).
 *
 * Defines struct oc_radio and bind helpers. Portable callers use
 * oc_radio_init / oc_radio_send / … from radio_hal.h only.
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

/* US915 bring-up defaults (125 kHz SF8). See docs/FCC-US915.md. */
#define OC_RADIO_US915_FREQ_HZ         903900000u
#define OC_RADIO_US915_SF_DEFAULT      8u
#define OC_RADIO_US915_BW_CODE_125K    0u
#define OC_RADIO_US915_CR_4_5          5u
#define OC_RADIO_US915_TX_CAP_DBM      14
#define OC_RADIO_US915_BUDGET_US_PER_H 36000000u /* ~1 % of an hour */
#define OC_RADIO_US915_MAX_FRAME_AIR_US 400000u
#define OC_RADIO_US915_MIN_TX_GAP_MS   100u
#define OC_RADIO_US915_DWELL_LIMIT_US  400000u
#define OC_RADIO_US915_DWELL_WINDOW_MS 20000u
#define OC_RADIO_US915_PREAMBLE        8u

typedef struct oc_radio_hw_ops {
	oc_radio_status_t (*cad)(void *ctx, oc_radio_cad_result_t *out);
	oc_radio_status_t (*send)(void *ctx, const uint8_t *buf, size_t len,
				  int8_t dbm);
	oc_radio_status_t (*recv)(void *ctx, uint8_t *buf, size_t cap,
				  size_t *out_len, oc_radio_rx_meta_t *meta,
				  uint32_t timeout_ms);
	oc_radio_status_t (*set_power)(void *ctx, int8_t dbm);
	oc_radio_status_t (*sleep)(void *ctx);
	uint64_t (*now_us)(void *ctx);
	uint32_t (*rand32)(void *ctx);
	void *ctx;
} oc_radio_hw_ops_t;

/*
 * Hardware/mock radio object. Storage owned by the app; bind ops before
 * oc_radio_init().
 */
struct oc_radio {
	oc_radio_cfg_t cfg;
	oc_radio_limits_t lim;
	oc_radio_hw_ops_t ops;
	void *hw; /* e.g. Zephyr device * */
	int8_t power_dbm;
	int8_t tx_power_cap_dbm;
	uint32_t mtu;
	uint8_t preamble;
	bool cad_before_tx;
	/* Hourly budget (lim.airtime_budget_us_per_h) */
	uint32_t duty_used_us;
	uint64_t duty_window_start_us;
	/* FCC dwell (radio-local; not in portable limits yet) */
	uint32_t dwell_limit_us;
	uint32_t dwell_window_ms;
	uint32_t dwell_used_us;
	uint32_t dwell_window_start_ms;
	uint32_t dwell_freq_hz;
	uint64_t last_tx_end_us;
	uint64_t rng;
	bool bound;
	bool inited;
};

void oc_radio_cfg_us915_defaults(oc_radio_cfg_t *cfg, oc_radio_limits_t *lim);

/* Attach hardware/mock ops before oc_radio_init. */
oc_radio_status_t oc_radio_sx1262_bind(oc_radio_t *radio,
				       const oc_radio_hw_ops_t *ops);

/* Host mock */
void oc_radio_mock_reset(void);
void oc_radio_mock_ops(oc_radio_hw_ops_t *ops);
void oc_radio_mock_set_time_us(uint64_t us);
void oc_radio_mock_advance_us(uint64_t us);
void oc_radio_mock_set_cad_busy(int busy);
void oc_radio_mock_queue_rx(const uint8_t *buf, size_t len, int16_t rssi,
			    int8_t snr);
uint32_t oc_radio_mock_tx_count(void);

#ifdef __ZEPHYR__
struct device;
/* Bind Zephyr lora0 then oc_radio_init — covers device pointer init cannot. */
oc_radio_status_t oc_radio_sx1262_bind_zephyr(oc_radio_t *radio,
					      const struct device *dev);
#endif

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_RADIO_SX1262_H */
