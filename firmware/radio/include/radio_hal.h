/*
 * OpenCollar radio HAL — proposed shape matching op-firmware's
 * ARCHITECTURE.md sketch for firmware/lora/radio_hal.h (op-fw-proto).
 *
 * This copy lives under firmware/radio/ until op-fw-proto lands the
 * canonical header on a proto-* branch. Keep signatures compatible.
 *
 * Portable: no Zephyr types. Topology-neutral (star or gossip).
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RADIO_HAL_H
#define OPENCOLLAR_RADIO_HAL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Error codes. RHAL_E_BUDGET is the hard airtime/duty refusal. */
#define RHAL_OK            0
#define RHAL_E_INVAL      (-1)
#define RHAL_E_IO         (-2)
#define RHAL_E_TIMEOUT    (-3)
#define RHAL_E_BUSY       (-4) /* CAD busy, or radio busy */
#define RHAL_E_BUDGET     (-5) /* hourly airtime / max-frame / min-gap refusal */
#define RHAL_E_POWER      (-6)
#define RHAL_E_NOSUP      (-7)

struct rhal_cfg {
	uint32_t freq_hz;
	uint8_t sf;            /* 7..10 for the US915 125 kHz bring-up preset */
	uint8_t bw_khz_code;   /* 0=125, 1=250, 2=500 (Semtech BW index style) */
	uint8_t cr;            /* 5=4/5 .. 8=4/8 */
	uint8_t sync_word;     /* private 0x12 default (not LoRaWAN) */
	int8_t tx_dbm;         /* default TX power; clamped to board/FCC max */
};

struct rhal_rx {
	uint8_t buf[255];
	uint8_t len;
	int16_t rssi_dbm;
	int8_t snr_db;
	uint64_t t_rx_us;
};

struct rhal_limits {
	uint32_t max_frame_airtime_us;   /* refuse longer frames (plan 1: ~222 B) */
	uint32_t airtime_budget_us_per_h;/* per-node hourly budget; send → E_BUDGET */
	uint16_t min_tx_gap_ms;          /* rate limit between our own sends */
	/* Bring-up extensions (Kconfig); keep zero to disable. */
	uint32_t dwell_limit_us;         /* 15.247(a)(1) hop dwell, default 400 ms */
	uint32_t dwell_window_ms;        /* default 20 000 */
	int8_t tx_power_cap_dbm;         /* absolute clamp, default +14 bring-up */
};

/* Optional per-send options (accepted by op-fw-proto). NULL → defaults. */
struct rhal_tx_opts {
	int8_t tx_dbm;           /* INT8_MIN = use current set_power */
	bool skip_cad;           /* test only */
	uint32_t cad_timeout_ms; /* 0 = default */
};

/* Platform clock + radio backend (Zephyr SX126x, host mock, sim). */
struct rhal_platform {
	uint64_t (*now_us)(void *ctx);
	int (*init)(void *ctx, const struct rhal_cfg *cfg);
	void (*deinit)(void *ctx);
	int (*set_power)(void *ctx, int8_t dbm);
	int (*cad)(void *ctx, uint32_t timeout_ms); /* 0 clear, 1 busy, <0 error */
	int (*send)(void *ctx, const uint8_t *buf, uint8_t len, int8_t dbm);
	int (*recv)(void *ctx, struct rhal_rx *out, uint32_t window_ms);
	int (*sleep)(void *ctx);
	void *ctx;
};

struct rhal; /* opaque */

int rhal_init(struct rhal *h, const struct rhal_cfg *cfg,
	      const struct rhal_limits *lim, const struct rhal_platform *plat);
void rhal_deinit(struct rhal *h);

int rhal_set_power(struct rhal *h, int8_t tx_dbm);
uint32_t rhal_airtime_us(const struct rhal *h, uint8_t len);
uint32_t rhal_airtime_left_us(const struct rhal *h);

/* at_us = 0 → now; otherwise wait until then (monotonic). Blocking until TX done.
 * Runs CAD unless opts->skip_cad. Returns RHAL_E_BUDGET on limit refusal. */
int rhal_send(struct rhal *h, const uint8_t *buf, uint8_t len, uint64_t at_us);
int rhal_send_ex(struct rhal *h, const uint8_t *buf, uint8_t len, uint64_t at_us,
		 const struct rhal_tx_opts *opts);

int rhal_recv(struct rhal *h, struct rhal_rx *out, uint32_t window_ms);

/* 1 = channel busy, 0 = clear, <0 = error. */
int rhal_cad(struct rhal *h, uint32_t timeout_ms);

int rhal_sleep(struct rhal *h);
uint64_t rhal_now_us(struct rhal *h);

/* Random backoff helpers for CAD/LBT and beacon jitter. */
void rhal_seed_rng(uint32_t seed);
uint32_t rhal_backoff_ms(uint32_t attempt, uint32_t min_ms, uint32_t max_ms);

#define RHAL_STORAGE_WORDS 80
struct rhal {
	uint32_t storage[RHAL_STORAGE_WORDS];
};

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_RADIO_HAL_H */
