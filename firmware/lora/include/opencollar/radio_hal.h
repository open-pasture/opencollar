/*
 * radio_hal.h — topology-neutral LoRa radio HAL for OpenCollar fence gossip.
 *
 * PLACEHOLDER names (oc_radio_*). Owned by firmware/lora (portable C, no
 * Zephyr). Hardware backends: firmware/radio (op-fw-radio). Host mock:
 * firmware/sim.
 *
 * Reconciles the op-fw-radio agreed shape (send opts / recv meta / CAD /
 * set_power / airtime / hard duty refusal / backoff) with
 * firmware/ARCHITECTURE.md § Radio HAL sketch (init, limits, sleep, clock,
 * max frame airtime, hourly budget, min TX gap).
 *
 * Every node both listens and transmits. Callers supply buffers; the HAL
 * does not allocate.
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
	OC_RADIO_ERR_DUTY = -5,        /* hourly airtime budget exhausted */
	OC_RADIO_ERR_NO_MEM = -6,      /* backend queue/buffer full */
	OC_RADIO_ERR_IO = -7,          /* underlying radio I/O failure */
	OC_RADIO_ERR_UNSUPPORTED = -8, /* optional feature not present */
	OC_RADIO_ERR_GAP = -9,         /* min_tx_gap_ms not yet elapsed */
	OC_RADIO_ERR_AIRTIME = -10     /* frame airtime > max_frame_airtime_us */
} oc_radio_status_t;

/* ---- CAD ---------------------------------------------------------------- */

typedef enum oc_radio_cad_result {
	OC_RADIO_CAD_FREE = 0,
	OC_RADIO_CAD_BUSY = 1
} oc_radio_cad_result_t;

/* ---- Config / limits (ARCHITECTURE.md sketch) --------------------------- */

typedef struct oc_radio_cfg {
	uint32_t freq_hz;
	uint8_t sf;          /* spreading factor */
	uint8_t bw_khz_code; /* backend-defined bandwidth code */
	uint8_t cr;          /* coding rate */
	uint8_t sync_word;
	int8_t tx_dbm; /* default TX power; clamped by backend */
} oc_radio_cfg_t;

typedef struct oc_radio_limits {
	uint32_t max_frame_airtime_us;    /* refuse longer frames (plan 1 ≈ 222 B) */
	uint32_t airtime_budget_us_per_h; /* hourly TX budget; send → ERR_DUTY */
	uint16_t min_tx_gap_ms;           /* min gap between this node's sends */
} oc_radio_limits_t;

/* ---- Send options (op-fw-radio agreed) ---------------------------------- */

/*
 * Per-packet overrides. Sentinel power = use current default (set_power /
 * init cfg). at_us == 0 means send as soon as gap/duty allow; non-zero is a
 * monotonic target from oc_radio_now_us (best-effort; backends MAY delay).
 */
typedef struct oc_radio_tx_opts {
	int8_t tx_power_dbm; /* INT8_MIN = use current default power */
	uint8_t flags;       /* reserved; must be 0 for now */
	uint16_t reserved;   /* reserved; must be 0 for now */
	uint64_t at_us;      /* 0 = now; else absolute oc_radio_now_us target */
} oc_radio_tx_opts_t;

#define OC_RADIO_TX_POWER_DEFAULT ((int8_t)(-128)) /* INT8_MIN */

static inline oc_radio_tx_opts_t oc_radio_tx_opts_default(void)
{
	oc_radio_tx_opts_t o;
	o.tx_power_dbm = OC_RADIO_TX_POWER_DEFAULT;
	o.flags = 0;
	o.reserved = 0;
	o.at_us = 0;
	return o;
}

/* ---- Recv metadata ------------------------------------------------------ */

typedef struct oc_radio_rx_meta {
	int16_t rssi_dbm;
	int8_t snr_db;
	uint8_t flags;         /* reserved; 0 for now */
	uint32_t timestamp_ms; /* coarse; prefer now_us for scheduling */
	uint64_t t_rx_us;      /* monotonic RX time; 0 if unknown */
} oc_radio_rx_meta_t;

/* ---- Opaque handle ------------------------------------------------------ */

typedef struct oc_radio oc_radio_t;

/* ---- Lifecycle ---------------------------------------------------------- */

/*
 * Initialise a backend-provided radio object with modulation cfg and
 * airtime limits. radio storage is owned by the backend (e.g. sim_world
 * node slot, or a static in firmware/radio). Idempotent re-init allowed.
 */
oc_radio_status_t oc_radio_init(oc_radio_t *radio, const oc_radio_cfg_t *cfg,
                                const oc_radio_limits_t *lim);

/* Enter low-power radio sleep. Wake on next send/recv/cad/init. */
oc_radio_status_t oc_radio_sleep(oc_radio_t *radio);

/*
 * Monotonic clock in microseconds (GNSS-disciplined on target; sim clock
 * on host). Used for scheduled TX (opts.at_us) and protocol timers.
 */
uint64_t oc_radio_now_us(const oc_radio_t *radio);

/* ---- Core ops ----------------------------------------------------------- */

/*
 * Transmit `len` bytes from `buf`.
 *
 * Returns OC_RADIO_OK on enqueue/success.
 * OC_RADIO_ERR_DUTY when the hourly airtime budget would be exceeded.
 * OC_RADIO_ERR_AIRTIME when airtime_us(len) > max_frame_airtime_us.
 * OC_RADIO_ERR_GAP when min_tx_gap_ms has not elapsed since last TX.
 * OC_RADIO_ERR_TOO_LARGE if len exceeds the backend MTU.
 * opts may be NULL for defaults (power default, at_us = now).
 */
oc_radio_status_t oc_radio_send(oc_radio_t *radio, const uint8_t *buf, size_t len,
                                const oc_radio_tx_opts_t *opts);

/*
 * Receive into caller-provided `buf` (capacity `cap`).
 *
 * Blocks up to `timeout_ms` (0 = non-blocking poll, UINT32_MAX = wait forever
 * until a frame or an error). On success writes *out_len and fills *out_meta
 * when out_meta is non-NULL.
 */
oc_radio_status_t oc_radio_recv(oc_radio_t *radio, uint8_t *buf, size_t cap,
                                size_t *out_len, oc_radio_rx_meta_t *out_meta,
                                uint32_t timeout_ms);

/*
 * Channel activity detection. Sets *out to FREE or BUSY.
 * timeout_ms is a CAD listen bound (0 = backend default).
 */
oc_radio_status_t oc_radio_cad(oc_radio_t *radio, oc_radio_cad_result_t *out);

/*
 * Set the default TX power used when send opts do not override it.
 * Clamped to board/FCC maximum by the backend.
 */
oc_radio_status_t oc_radio_set_power(oc_radio_t *radio, int8_t dbm);

/* ---- Airtime and duty cycle --------------------------------------------- */

/* Estimated time-on-air (µs) for `len` payload bytes (Semtech AN1200.13). */
uint32_t oc_radio_airtime_us(const oc_radio_t *radio, size_t len);

/*
 * Remaining hourly TX airtime budget in microseconds (ARCHITECTURE:
 * rhal_airtime_left_us). 0 ⇒ next positive-airtime send returns ERR_DUTY.
 */
uint32_t oc_radio_duty_budget_us(const oc_radio_t *radio);

/* Alias matching the architecture sketch name. */
static inline uint32_t oc_radio_airtime_left_us(const oc_radio_t *radio)
{
	return oc_radio_duty_budget_us(radio);
}

/* ---- Random backoff helpers --------------------------------------------- */

uint32_t oc_radio_backoff_ms(oc_radio_t *radio, uint32_t lo_ms, uint32_t hi_ms);

/* RFC 6206-style: uniform time in [I/2, I] for interval I (ms). */
uint32_t oc_radio_trickle_t_ms(oc_radio_t *radio, uint32_t interval_ms);

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_RADIO_HAL_H */
