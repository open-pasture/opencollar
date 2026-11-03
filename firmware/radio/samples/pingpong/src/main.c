/*
 * Symmetric ping/pong — opencollar/radio_hal.h (init/sleep/now_us/limits).
 * SPDX-License-Identifier: Apache-2.0
 */
#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <string.h>

#include "opencollar/radio_hal.h"
#include "opencollar/radio_sx1262.h"
#include "radio_sched.h"

LOG_MODULE_REGISTER(pingpong, LOG_LEVEL_INF);

#define MAGIC0 0x4Fu
#define MAGIC1 0x43u
#define KIND_PING 1u
#define KIND_PONG 2u

struct pkt {
	uint8_t magic0;
	uint8_t magic1;
	uint8_t kind;
	uint8_t seq;
	uint32_t t_ms;
} __attribute__((packed));

static oc_radio_t g_radio;
static struct radio_sched g_sched;
static uint32_t g_tx_ok, g_tx_fail, g_rx_ping, g_rx_pong;
static uint8_t g_seq;

static void send_pkt(uint8_t kind, uint8_t seq)
{
	struct pkt p;
	oc_radio_tx_opts_t opts = oc_radio_tx_opts_default();
	oc_radio_status_t st;

	p.magic0 = MAGIC0;
	p.magic1 = MAGIC1;
	p.kind = kind;
	p.seq = seq;
	p.t_ms = k_uptime_get_32();

	st = oc_radio_send(&g_radio, (const uint8_t *)&p, sizeof(p), &opts);
	if (st == OC_RADIO_ERR_BUSY) {
		uint32_t bo = oc_radio_backoff_ms(&g_radio, 20, 200);

		LOG_INF("CAD busy, backoff %u ms", bo);
		k_msleep(bo);
		st = oc_radio_send(&g_radio, (const uint8_t *)&p, sizeof(p),
				   &opts);
	}
	if (st == OC_RADIO_OK) {
		g_tx_ok++;
		LOG_INF("tx kind=%u seq=%u air=%u left=%u", kind, seq,
			oc_radio_airtime_us(&g_radio, sizeof(p)),
			oc_radio_duty_budget_us(&g_radio));
	} else {
		g_tx_fail++;
		LOG_WRN("tx fail st=%d", (int)st);
	}
}

static void handle_rx(uint32_t window_ms)
{
	uint8_t buf[64];
	size_t n = 0;
	oc_radio_rx_meta_t meta;
	oc_radio_status_t st;
	struct pkt p;

	st = oc_radio_recv(&g_radio, buf, sizeof(buf), &n, &meta, window_ms);
	if (st != OC_RADIO_OK || n < sizeof(p)) {
		return;
	}
	memcpy(&p, buf, sizeof(p));
	if (p.magic0 != MAGIC0 || p.magic1 != MAGIC1) {
		return;
	}
	if (p.kind == KIND_PING) {
		g_rx_ping++;
		LOG_INF("rx PING seq=%u rssi=%d snr=%d t_us=%llu | tx=%u/%u p=%u/%u",
			p.seq, meta.rssi_dbm, meta.snr_db,
			(unsigned long long)meta.t_rx_us, g_tx_ok, g_tx_fail,
			g_rx_ping, g_rx_pong);
		send_pkt(KIND_PONG, p.seq);
	} else if (p.kind == KIND_PONG) {
		g_rx_pong++;
		LOG_INF("rx PONG seq=%u rssi=%d snr=%d | tx=%u/%u p=%u/%u",
			p.seq, meta.rssi_dbm, meta.snr_db, g_tx_ok, g_tx_fail,
			g_rx_ping, g_rx_pong);
	}
}

int main(void)
{
	const struct device *lora = DEVICE_DT_GET(DT_ALIAS(lora0));
	oc_radio_cfg_t cfg;
	oc_radio_limits_t lim;
	struct radio_sched_cfg scfg;
	uint32_t next_ping_ms = 0;
	uint32_t now_ms, wake_ms;
	enum radio_sched_action act;
	oc_radio_status_t st;

	oc_radio_cfg_us915_defaults(&cfg, &lim);
	cfg.freq_hz = CONFIG_RADIO_FREQ_HZ;
	cfg.sf = CONFIG_RADIO_SF;
	cfg.tx_dbm = CONFIG_RADIO_TX_CAP_DBM;

	st = oc_radio_sx1262_bind_zephyr(&g_radio, lora);
	if (st != OC_RADIO_OK) {
		LOG_ERR("bind failed %d — check overlay/shield", (int)st);
		return 0;
	}
	st = oc_radio_init(&g_radio, &cfg, &lim);
	if (st != OC_RADIO_OK) {
		LOG_ERR("init failed %d", (int)st);
		return 0;
	}

	memset(&scfg, 0, sizeof(scfg));
	scfg.rx_period_ms = CONFIG_RADIO_RX_PERIOD_MS;
	scfg.rx_window_ms = CONFIG_RADIO_RX_WINDOW_MS;
	scfg.beacon_period_ms = CONFIG_RADIO_BEACON_PERIOD_MS ?
				CONFIG_RADIO_BEACON_PERIOD_MS :
				0xffffffffu;
	scfg.beacon_jitter_ms = CONFIG_RADIO_BEACON_JITTER_MS;
	scfg.cad_before_beacon = true;
	radio_sched_init(&g_sched, &scfg, k_uptime_get_32());

	LOG_INF("pingpong sf=%u freq=%u now_us=%llu initiator=%d", cfg.sf,
		cfg.freq_hz, (unsigned long long)oc_radio_now_us(&g_radio),
		IS_ENABLED(CONFIG_RADIO_PINGPONG_INITIATOR));

	if (IS_ENABLED(CONFIG_RADIO_PINGPONG_INITIATOR)) {
		next_ping_ms = k_uptime_get_32() + 500;
	}

	for (;;) {
		now_ms = k_uptime_get_32();
		if (IS_ENABLED(CONFIG_RADIO_PINGPONG_INITIATOR) &&
		    now_ms >= next_ping_ms) {
			send_pkt(KIND_PING, g_seq++);
			next_ping_ms = now_ms + CONFIG_RADIO_PINGPONG_INTERVAL_MS +
				       oc_radio_backoff_ms(&g_radio, 0, 200);
		}

		act = radio_sched_poll(&g_sched, now_ms, &wake_ms);
		switch (act) {
		case RADIO_SCHED_RX_WINDOW:
			handle_rx(CONFIG_RADIO_RX_WINDOW_MS);
			break;
		case RADIO_SCHED_BEACON:
			if (CONFIG_RADIO_BEACON_PERIOD_MS) {
				uint8_t b[6] = { MAGIC0, MAGIC1, 0x10, g_seq,
						 (uint8_t)(now_ms & 0xff),
						 (uint8_t)((now_ms >> 8) & 0xff) };
				oc_radio_tx_opts_t o = oc_radio_tx_opts_default();

				(void)oc_radio_send(&g_radio, b, sizeof(b), &o);
			}
			radio_sched_beacon_done(&g_sched, k_uptime_get_32());
			break;
		case RADIO_SCHED_CAD_WAKE: {
			oc_radio_cad_result_t c;

			(void)oc_radio_cad(&g_radio, &c);
			break;
		}
		case RADIO_SCHED_SLEEP:
		default:
			(void)oc_radio_sleep(&g_radio);
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
