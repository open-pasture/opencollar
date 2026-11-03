/*
 * Symmetric ping/pong link test for SX1262 bring-up.
 * Both sides listen in RX windows; either may initiate pings.
 * SPDX-License-Identifier: Apache-2.0
 */
#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/random/random.h>
#include <string.h>
#include <stdio.h>

#include "radio_hal.h"
#include "radio_sched.h"
#include "radio_us915.h"
#include "rhal_zephyr.h"

LOG_MODULE_REGISTER(pingpong, LOG_LEVEL_INF);

#define MAGIC0 0x4Fu /* 'O' */
#define MAGIC1 0x43u /* 'C' */
#define KIND_PING 1u
#define KIND_PONG 2u

struct pkt {
	uint8_t magic0;
	uint8_t magic1;
	uint8_t kind;
	uint8_t seq;
	uint32_t t_ms;
} __attribute__((packed));

static struct rhal g_hal;
static struct rhal_platform g_plat;
static struct radio_sched g_sched;

static uint32_t g_tx_ok;
static uint32_t g_tx_fail;
static uint32_t g_rx_ping;
static uint32_t g_rx_pong;
static uint8_t g_seq;

static void send_pkt(uint8_t kind, uint8_t seq)
{
	struct pkt p;
	struct rhal_tx_opts opts;
	int rc;

	p.magic0 = MAGIC0;
	p.magic1 = MAGIC1;
	p.kind = kind;
	p.seq = seq;
	p.t_ms = k_uptime_get_32();

	memset(&opts, 0, sizeof(opts));
	opts.tx_dbm = INT8_MIN;
	opts.skip_cad = false;
	opts.cad_timeout_ms = 50;

	rc = rhal_send_ex(&g_hal, (const uint8_t *)&p, sizeof(p), 0, &opts);
	if (rc == RHAL_E_BUSY) {
		uint32_t bo = rhal_backoff_ms(1, 20, 200);

		LOG_INF("CAD busy, backoff %u ms", bo);
		k_msleep(bo);
		rc = rhal_send_ex(&g_hal, (const uint8_t *)&p, sizeof(p), 0, &opts);
	}
	if (rc == RHAL_OK) {
		g_tx_ok++;
		LOG_INF("tx kind=%u seq=%u air=%u us left=%u",
			kind, seq, rhal_airtime_us(&g_hal, sizeof(p)),
			rhal_airtime_left_us(&g_hal));
	} else {
		g_tx_fail++;
		LOG_WRN("tx fail rc=%d (budget/busy/io)", rc);
	}
}

static void handle_rx(void)
{
	struct rhal_rx rx;
	struct pkt p;
	int rc;

	rc = rhal_recv(&g_hal, &rx, CONFIG_RADIO_RX_WINDOW_MS);
	if (rc != RHAL_OK) {
		return;
	}
	if (rx.len < sizeof(p)) {
		return;
	}
	memcpy(&p, rx.buf, sizeof(p));
	if (p.magic0 != MAGIC0 || p.magic1 != MAGIC1) {
		return;
	}
	if (p.kind == KIND_PING) {
		g_rx_ping++;
		LOG_INF("rx PING seq=%u rssi=%d snr=%d | tx=%u/%u rx_ping=%u rx_pong=%u",
			p.seq, rx.rssi_dbm, rx.snr_db,
			g_tx_ok, g_tx_fail, g_rx_ping, g_rx_pong);
		send_pkt(KIND_PONG, p.seq);
	} else if (p.kind == KIND_PONG) {
		g_rx_pong++;
		LOG_INF("rx PONG seq=%u rssi=%d snr=%d | tx=%u/%u rx_ping=%u rx_pong=%u",
			p.seq, rx.rssi_dbm, rx.snr_db,
			g_tx_ok, g_tx_fail, g_rx_ping, g_rx_pong);
	}
}

int main(void)
{
	const struct device *lora = DEVICE_DT_GET(DT_ALIAS(lora0));
	struct rhal_cfg cfg;
	struct rhal_limits lim;
	struct radio_sched_cfg scfg;
	uint32_t next_ping_ms = 0;
	uint32_t now_ms;
	uint32_t wake_ms;
	enum radio_sched_action act;
	int rc;

	if (!device_is_ready(lora)) {
		LOG_ERR("lora0 not ready — check overlay/shield wiring");
		return 0;
	}

	rhal_us915_default_cfg(&cfg);
	cfg.freq_hz = CONFIG_RADIO_FREQ_HZ;
	cfg.sf = CONFIG_RADIO_SF;
	cfg.tx_dbm = CONFIG_RADIO_TX_CAP_DBM;
	rhal_us915_default_limits(&lim);
	lim.tx_power_cap_dbm = CONFIG_RADIO_TX_CAP_DBM;

	rc = rhal_zephyr_platform(&g_plat, lora);
	if (rc != RHAL_OK) {
		LOG_ERR("platform bind failed %d", rc);
		return 0;
	}
	rhal_seed_rng(sys_rand32_get());
	rc = rhal_init(&g_hal, &cfg, &lim, &g_plat);
	if (rc != RHAL_OK) {
		LOG_ERR("rhal_init failed %d", rc);
		return 0;
	}

	memset(&scfg, 0, sizeof(scfg));
	scfg.rx_period_ms = CONFIG_RADIO_RX_PERIOD_MS;
	scfg.rx_window_ms = CONFIG_RADIO_RX_WINDOW_MS;
	scfg.beacon_period_ms = CONFIG_RADIO_BEACON_PERIOD_MS ?
				CONFIG_RADIO_BEACON_PERIOD_MS : 0xffffffffu;
	scfg.beacon_jitter_ms = CONFIG_RADIO_BEACON_JITTER_MS;
	scfg.cad_before_beacon = true;
	scfg.cad_wake_period_ms = 0;
	radio_sched_init(&g_sched, &scfg, k_uptime_get_32());

	LOG_INF("pingpong ready sf=%u bw=125kHz freq=%u initiator=%d",
		cfg.sf, cfg.freq_hz, IS_ENABLED(CONFIG_RADIO_PINGPONG_INITIATOR));
	LOG_INF("airtime 16 B ≈ %u us", rhal_airtime_us(&g_hal, 16));

	if (IS_ENABLED(CONFIG_RADIO_PINGPONG_INITIATOR)) {
		next_ping_ms = k_uptime_get_32() + 500;
	}

	for (;;) {
		now_ms = k_uptime_get_32();

		if (IS_ENABLED(CONFIG_RADIO_PINGPONG_INITIATOR) &&
		    now_ms >= next_ping_ms) {
			send_pkt(KIND_PING, g_seq++);
			next_ping_ms = now_ms + CONFIG_RADIO_PINGPONG_INTERVAL_MS +
				       (rhal_backoff_ms(0, 0, 200));
		}

		act = radio_sched_poll(&g_sched, now_ms, &wake_ms);
		switch (act) {
		case RADIO_SCHED_RX_WINDOW:
			handle_rx();
			break;
		case RADIO_SCHED_BEACON:
			/* Optional freshness advert for gossip bring-up. */
			if (CONFIG_RADIO_BEACON_PERIOD_MS) {
				uint8_t b[6] = { MAGIC0, MAGIC1, 0x10, g_seq,
						 (uint8_t)(now_ms & 0xff),
						 (uint8_t)((now_ms >> 8) & 0xff) };
				struct rhal_tx_opts o = { .tx_dbm = INT8_MIN };

				(void)rhal_send_ex(&g_hal, b, sizeof(b), 0, &o);
				radio_sched_beacon_done(&g_sched, k_uptime_get_32());
			} else {
				radio_sched_beacon_done(&g_sched, now_ms);
			}
			break;
		case RADIO_SCHED_CAD_WAKE:
			(void)rhal_cad(&g_hal, 20);
			break;
		case RADIO_SCHED_SLEEP:
		default:
			rhal_sleep(&g_hal);
			if (wake_ms > now_ms) {
				k_msleep(wake_ms - now_ms);
			} else {
				k_msleep(10);
			}
			break;
		}
	}
	return 0;
}
