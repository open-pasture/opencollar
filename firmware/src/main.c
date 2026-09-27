/*
 * OpenCollar 0.2: GNSS fix -> slots and geofence -> audio cue, logged over
 * serial, with provisioning and bench commands on the same serial port.
 *
 * Boot: provisioning, config and slots come from flash (NVS); the latest
 * active boundary is enforced at once, staged ones wait for the first GNSS
 * fix. No boundary means no fence and no cues. GNSS time is the only clock
 * for boundary activation. Everything else is in app.c, which host tests
 * drive the same way. Boundary download over LTE waits for the SIM; until
 * then a signed command can be pasted on the console (`boundary <command>`).
 */
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/printk.h>
#include <modem/lte_lc.h>
#include <modem/nrf_modem_lib.h>
#include <nrf_modem_gnss.h>

#include "app.h"
#include "boundary.h"
#include "buzzer.h"
#include "console.h"
#include "store.h"

LOG_MODULE_REGISTER(opencollar, LOG_LEVEL_INF);

static const struct geofence_config geofence_defaults = {
	.warn_m = 5.0,
	.hysteresis_m = 1.0,
	.max_accuracy_m = 10.0,
};

static const struct cue_config cue_cfg = {
	.warn_freq_hz = 2730, /* Buzzer's resonant frequency: loudest */
	.outside_freq_hz = 1000,
	.beep_ms = 300,
	.max_active_ms = 20000,
	.rest_ms = 30000,
	.outside_max_ms = 10000,
};

struct fix {
	bool valid;
	bool has_time;
	double lat;
	double lon;
	float accuracy;
	uint8_t sats_tracked;
	uint8_t sats_in_fix;
	int64_t utc;
};

K_MSGQ_DEFINE(fix_q, sizeof(struct fix), 4, 8);
static struct k_poll_signal console_sig = K_POLL_SIGNAL_INITIALIZER(console_sig);

/* Everything the collar knows, in static RAM (see BUILD-LOG for the budget) */
static struct app app;
static char reply[256];
static uint32_t store_errors_seen;

static void gnss_event_handler(int event)
{
	struct nrf_modem_gnss_pvt_data_frame pvt;
	struct fix f = {0};

	if (event != NRF_MODEM_GNSS_EVT_PVT) {
		return;
	}
	if (nrf_modem_gnss_read(&pvt, sizeof(pvt), NRF_MODEM_GNSS_DATA_PVT) != 0) {
		return;
	}

	for (int i = 0; i < NRF_MODEM_GNSS_MAX_SATELLITES; i++) {
		if (pvt.sv[i].sv == 0) {
			continue;
		}
		f.sats_tracked++;
		if (pvt.sv[i].flags & NRF_MODEM_GNSS_SV_FLAG_USED_IN_FIX) {
			f.sats_in_fix++;
		}
	}

	f.valid = pvt.flags & NRF_MODEM_GNSS_PVT_FLAG_FIX_VALID;
	f.lat = pvt.latitude;
	f.lon = pvt.longitude;
	f.accuracy = pvt.accuracy;
	if (f.valid) {
		/* The fix's own UTC: the clock for boundary activation */
		f.has_time = true;
		f.utc = proto_time_civil(pvt.datetime.year, pvt.datetime.month, pvt.datetime.day,
					 pvt.datetime.hour, pvt.datetime.minute,
					 pvt.datetime.seconds);
	}

	/* Drop the fix if the main loop is behind; the next one is a second away */
	k_msgq_put(&fix_q, &f, K_NO_WAIT);
}

static int gnss_start(void)
{
	int err;

	err = nrf_modem_lib_init();
	if (err) {
		LOG_ERR("Modem library init failed: %d", err);
		return err;
	}

	err = lte_lc_system_mode_set(LTE_LC_SYSTEM_MODE_LTEM_GPS, LTE_LC_SYSTEM_MODE_PREFER_AUTO);
	if (err) {
		LOG_ERR("System mode set failed: %d", err);
		return err;
	}

	/* GNSS only until the SIM is in: LTE isn't needed for local fencing */
	err = lte_lc_func_mode_set(LTE_LC_FUNC_MODE_ACTIVATE_GNSS);
	if (err) {
		LOG_ERR("Failed to activate GNSS: %d", err);
		return err;
	}

	err = nrf_modem_gnss_event_handler_set(gnss_event_handler);
	if (!err) {
		err = nrf_modem_gnss_fix_interval_set(1);
	}
	if (!err) {
		err = nrf_modem_gnss_start();
	}
	if (err) {
		LOG_ERR("GNSS start failed: %d", err);
	}
	return err;
}

static void log_ack(const struct slot_ack *ack)
{
	char at[24] = "-";

	if (ack->has_at) {
		proto_time_format(ack->at, at, sizeof(at));
	}
	LOG_INF("ack v%u %s%s%s at %s (%u pending)", ack->version, ack_status_str(ack->status),
		ack->code ? " " : "", reject_str(ack->code), at, app.acks.n);
}

static void check_store(void)
{
	uint32_t errors = app.slots.store_errors + app.cfg.store_errors;

	if (errors != store_errors_seen) {
		LOG_WRN("Flash writes failed: %u so far", errors);
		store_errors_seen = errors;
	}
}

static void handle_fix(const struct fix *f)
{
	static int64_t last_no_fix_log;
	int64_t now = k_uptime_get();
	struct app_fix_in in = {
		.valid = f->valid,
		.lat = f->lat,
		.lon = f->lon,
		.accuracy_m = f->accuracy,
		.has_time = f->has_time,
		.utc = f->utc,
	};
	struct app_fix_out out = app_fix(&app, &in, now);
	struct episode ep;

	if (out.applied) {
		LOG_INF("event: staged boundary v%u now in force", out.ack.version);
		log_ack(&out.ack);
		check_store();
	}

	if (!f->valid) {
		if (now - last_no_fix_log >= 10000) {
			last_no_fix_log = now;
			LOG_INF("searching: %u tracked, %u in fix", f->sats_tracked, f->sats_in_fix);
		}
		return;
	}

	if (!out.fenced) {
		LOG_INF("fix %.6f,%.6f acc=%.1fm sats=%u (no boundary)", f->lat, f->lon,
			(double)f->accuracy, f->sats_in_fix);
		return;
	}

	if (out.cmd.active) {
		buzzer_play(out.cmd.freq_hz, out.cmd.volume, out.cmd.duration_ms);
	}

	LOG_INF("fix %.6f,%.6f acc=%.1fm sats=%u v%u state=%s margin=%.1fm ring=%d%s%s cue=%s vol=%u",
		f->lat, f->lon, (double)f->accuracy, f->sats_in_fix, out.version,
		geofence_state_str(out.r.state), out.r.margin_m, out.r.nearest_ring,
		out.r.degraded ? " (degraded)" : "",
		app.cue.mode == CUE_MODE_TRACK ? " (track)" : (app.cue.armed ? "" : " (unarmed)"),
		out.cmd.active ? cue_kind_str(out.cmd.kind) : "off", out.cmd.volume);

	if (out.r.changed) {
		LOG_INF("event: state -> %s", geofence_state_str(out.r.state));
	}
	while (cue_take_episode(&app.cue, &ep)) {
		LOG_INF("episode: %s ring=%d cues=%u max=%u min_margin=%.1fm %lld ms",
			episode_outcome_str(ep.outcome), ep.ring, ep.cues, ep.max_level,
			ep.min_margin_m, ep.end - ep.start);
	}
}

static void handle_line(void)
{
	size_t len;
	bool overflow;
	const char *line = console_line(&len, &overflow);
	uint32_t acks_before = app.acks.n;
	uint32_t version_before = app.fence ? app.fence->version : 0;
	bool fenced_before = app.fence != NULL;

	if (!line) {
		return;
	}
	app_line(&app, line, len, overflow, k_uptime_get(), reply, sizeof(reply));
	console_release();
	if (reply[0]) {
		printk("%s\n", reply);
	}
	if (app.acks.n != acks_before && app.acks.n > 0) {
		log_ack(&app.acks.q[app.acks.n - 1]);
	}
	if (app.fence && (!fenced_before || app.fence->version != version_before)) {
		LOG_INF("event: boundary v%u in force: %d rings, %d vertices", app.fence->version,
			app.fence->rings, app.fence->n);
	} else if (!app.fence && fenced_before) {
		LOG_INF("event: no boundary: no cues");
	}
	check_store();
}

static void log_boot_state(void)
{
	const struct slot_hdr *act = slots_active(&app.slots);
	uint32_t staged = app.slots.n - (act ? 1 : 0);

	if (!app.prov.ok) {
		LOG_INF("Not provisioned: GNSS only. Paste the card: provision {...}");
		return;
	}
	LOG_INF("Collar %s, herd %s, config %s", app.prov.collar_id.s, app_herd(&app)->s,
		app.cfg.has ? "stored" : "none");
	if (act && app.fence) {
		LOG_INF("Boundary v%u enforced from flash: %d rings, %d vertices%s", act->version,
			app.fence->rings, app.fence->n,
			(act->flags & SLOT_F_TRACK) ? ", track mode" : "");
	} else {
		LOG_INF("No boundary: no cues");
	}
	if (staged) {
		LOG_INF("%u staged boundaries wait for the first GNSS fix", staged);
	}
	if (app.acks.n) {
		LOG_INF("%u acks pending", app.acks.n);
	}
}

int main(void)
{
	struct fix f;
	int err;
	struct k_poll_event events[] = {
		K_POLL_EVENT_STATIC_INITIALIZER(K_POLL_TYPE_MSGQ_DATA_AVAILABLE,
						K_POLL_MODE_NOTIFY_ONLY, &fix_q, 0),
		K_POLL_EVENT_STATIC_INITIALIZER(K_POLL_TYPE_SIGNAL, K_POLL_MODE_NOTIFY_ONLY,
						&console_sig, 0),
	};

	LOG_INF("OpenCollar %s starting", APP_FW_VERSION);

	err = store_init();
	if (err) {
		LOG_ERR("Flash storage unavailable (%d): nothing will be kept over a reboot", err);
	}

	app_init(&app, &cue_cfg, &geofence_defaults);
	app_boot(&app, k_uptime_get());
	log_boot_state();

#ifdef CONFIG_OPENCOLLAR_BENCH_BOUNDARY
	if (app_bench(&app, boundary_vertices, ARRAY_SIZE(boundary_vertices), k_uptime_get())) {
		LOG_INF("Bench boundary loaded as v0: %u vertices",
			(unsigned)ARRAY_SIZE(boundary_vertices));
	}
#endif

	err = console_init(&console_sig);
	if (err) {
		LOG_ERR("Console input unavailable: %d", err);
	}

	if (buzzer_init() == 0) {
		/* Short chirp so you know the cue path works at boot (not a cue) */
		buzzer_play(cue_cfg.warn_freq_hz, 2, 150);
	}

	if (gnss_start() == 0) {
		LOG_INF("GNSS started");
	}

	while (true) {
		k_poll(events, ARRAY_SIZE(events), K_FOREVER);

		if (events[0].state == K_POLL_STATE_MSGQ_DATA_AVAILABLE) {
			while (k_msgq_get(&fix_q, &f, K_NO_WAIT) == 0) {
				handle_fix(&f);
			}
		}
		if (events[1].state == K_POLL_STATE_SIGNALED) {
			k_poll_signal_reset(&console_sig);
			handle_line();
		}
		events[0].state = K_POLL_STATE_NOT_READY;
		events[1].state = K_POLL_STATE_NOT_READY;
	}

	return 0;
}
