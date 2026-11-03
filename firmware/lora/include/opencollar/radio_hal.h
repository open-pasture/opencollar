/*
 * radio_hal.h — topology-neutral LoRa radio HAL for OpenCollar fence gossip.
 *
 * Owned by firmware/lora (portable C, no Zephyr). Hardware backends live in
 * firmware/radio (op-fw-radio); host virtual radio lives in firmware/sim.
 *
 * Every node both listens and transmits. Callers supply buffers; the HAL
 * does not allocate. Integers are host-endian except where noted on the wire.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RADIO_HAL_H
#define OPENCOLLAR_RADIO_HAL_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- Status ------------------------------------------------------------- */

typedef enum oc_radio_status {
	OC_RADIO_OK = 0,
	OC_RADIO_ERR_PARAM = -1,       /* null/invalid argument */
	OC_RADIO_ERR_TIMEOUT = -2,     /* recv timed out with no frame */
	OC_RADIO_ERR_BUSY = -3,        /* CAD found the channel busy */
	OC_RADIO_ERR_TOO_LARGE = -4,   /* frame exceeds radio MTU */
	OC_RADIO_ERR_DUTY = -5,        /* hard duty-cycle budget exhausted */
	OC_RADIO_ERR_NO_MEM = -6,      /* backend queue/buffer full */
	OC_RADIO_ERR_IO = -7,          /* underlying radio I/O failure */
	OC_RADIO_ERR_UNSUPPORTED = -8  /* optional feature not present */
} oc_radio_status_t;

/* ---- CAD ---------------------------------------------------------------- */

typedef enum oc_radio_cad_result {
	OC_RADIO_CAD_FREE = 0,
	OC_RADIO_CAD_BUSY = 1
} oc_radio_cad_result_t;

/* ---- Send options ------------------------------------------------------- */

/*
 * Per-packet overrides. Fields that are left at the sentinel values use the
 * radio's current defaults (see oc_radio_set_power).
 */
typedef struct oc_radio_tx_opts {
	int8_t tx_power_dbm; /* INT8_MIN = use current default power */
	uint8_t flags;       /* reserved; must be 0 for now */
	uint16_t reserved;   /* reserved; must be 0 for now */
} oc_radio_tx_opts_t;

#define OC_RADIO_TX_POWER_DEFAULT ((int8_t)(-128)) /* INT8_MIN */

static inline oc_radio_tx_opts_t oc_radio_tx_opts_default(void)
{
	oc_radio_tx_opts_t o;
	o.tx_power_dbm = OC_RADIO_TX_POWER_DEFAULT;
	o.flags = 0;
	o.reserved = 0;
	return o;
}

/* ---- Recv metadata ------------------------------------------------------ */

typedef struct oc_radio_rx_meta {
	int16_t rssi_dbm;  /* estimated RSSI of the received frame */
	int8_t snr_db;     /* SNR in dB (LoRa); 0 if unavailable */
	uint8_t flags;     /* reserved; 0 for now */
	uint32_t timestamp_ms; /* optional backend clock; 0 if unknown */
} oc_radio_rx_meta_t;

/* ---- Opaque handle ------------------------------------------------------ */

typedef struct oc_radio oc_radio_t;

/* ---- Core ops ----------------------------------------------------------- */

/*
 * Transmit `len` bytes from `buf`.
 *
 * Returns OC_RADIO_OK on enqueue/success.
 * Returns OC_RADIO_ERR_DUTY when the hard duty-cycle budget would be exceeded
 * (the frame is not sent). Returns OC_RADIO_ERR_TOO_LARGE if len exceeds the
 * backend MTU. opts may be NULL for defaults.
 */
oc_radio_status_t oc_radio_send(oc_radio_t *radio,
                                const uint8_t *buf, size_t len,
                                const oc_radio_tx_opts_t *opts);

/*
 * Receive into caller-provided `buf` (capacity `cap`).
 *
 * Blocks up to `timeout_ms` (0 = non-blocking poll, UINT32_MAX = wait forever
 * until a frame or an error). On success writes the frame length via
 * *out_len and fills *out_meta when out_meta is non-NULL.
 *
 * Returns OC_RADIO_OK, OC_RADIO_ERR_TIMEOUT, or another error.
 */
oc_radio_status_t oc_radio_recv(oc_radio_t *radio,
                                uint8_t *buf, size_t cap, size_t *out_len,
                                oc_radio_rx_meta_t *out_meta,
                                uint32_t timeout_ms);

/*
 * Channel activity detection. Sets *out to FREE or BUSY.
 * Returns OC_RADIO_OK or an I/O error.
 */
oc_radio_status_t oc_radio_cad(oc_radio_t *radio, oc_radio_cad_result_t *out);

/*
 * Set the default TX power used when send opts do not override it.
 * Returns OC_RADIO_OK, OC_RADIO_ERR_PARAM (out of range), or UNSUPPORTED.
 */
oc_radio_status_t oc_radio_set_power(oc_radio_t *radio, int8_t dbm);

/* ---- Airtime and duty cycle --------------------------------------------- */

/*
 * Estimated time-on-air in microseconds for a frame of `len` payload bytes
 * under the radio's current modulation. Pure query; does not send.
 */
uint32_t oc_radio_airtime_us(const oc_radio_t *radio, size_t len);

/*
 * Remaining hard duty-cycle budget in microseconds within the backend's
 * regulatory window (e.g. rolling 1 hour / 1 %). 0 means the next send of
 * any positive airtime will return OC_RADIO_ERR_DUTY until budget recovers.
 */
uint32_t oc_radio_duty_budget_us(const oc_radio_t *radio);

/* ---- Random backoff helpers --------------------------------------------- */

/*
 * Draw a uniform random delay in [lo_ms, hi_ms] inclusive using the radio's
 * RNG (or a backend-seeded PRNG on the host sim). Used by Trickle / serve
 * suppression. Returns lo_ms if hi_ms < lo_ms.
 */
uint32_t oc_radio_backoff_ms(oc_radio_t *radio, uint32_t lo_ms, uint32_t hi_ms);

/*
 * RFC 6206-style Trickle interval helper: return a time uniformly in
 * [I/2, I] for interval I (milliseconds). I of 0 returns 0.
 */
uint32_t oc_radio_trickle_t_ms(oc_radio_t *radio, uint32_t interval_ms);

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_RADIO_HAL_H */
