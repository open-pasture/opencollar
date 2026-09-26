/*
 * OpenCollar V0: GNSS fix -> local geofence -> audio cue, logged over serial.
 *
 * Runs with no network. The boundary is compiled in (see boundary.h) until
 * boundary download over LTE is added.
 */
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <modem/lte_lc.h>
#include <modem/nrf_modem_lib.h>
#include <nrf_modem_gnss.h>

#include "boundary.h"
#include "buzzer.h"
#include "cue.h"
#include "geofence.h"

LOG_MODULE_REGISTER(opencollar, LOG_LEVEL_INF);

#define ARRAY_LEN(a) (sizeof(a) / sizeof((a)[0]))

static const struct geofence_config geofence_cfg = {
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
	double lat;
	double lon;
	float accuracy;
	uint8_t sats_tracked;
	uint8_t sats_in_fix;
};

K_MSGQ_DEFINE(fix_q, sizeof(struct fix), 4, 4);

static struct geofence fence;
static struct cue cue;

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

	/* GNSS only for V0: no SIM yet, and LTE isn't needed for local fencing */
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

/*
 * Every boundary goes through here: at boot now, and from the LTE download
 * once that exists. The fence starts unarmed under each new boundary, so an
 * animal it leaves outside is never cued (see cue.h).
 */
static int apply_boundary(const struct geo_point *vertices, int n, uint32_t version)
{
	if (geofence_init(&fence, &geofence_cfg, vertices, n, version) != 0) {
		return -1;
	}
	cue_rearm(&cue);
	return 0;
}

static void handle_fix(const struct fix *f)
{
	static int64_t last_no_fix_log;
	int64_t now = k_uptime_get();

	if (!f->valid) {
		if (now - last_no_fix_log >= 10000) {
			last_no_fix_log = now;
			LOG_INF("searching: %u tracked, %u in fix", f->sats_tracked, f->sats_in_fix);
		}
		return;
	}

	struct geo_point p = {.lat = f->lat, .lon = f->lon};
	struct geofence_result r = geofence_update(&fence, p, f->accuracy);
	struct cue_command cmd = cue_update(&cue, &r, geofence_cfg.warn_m, now);

	if (cmd.active) {
		buzzer_play(cmd.freq_hz, cmd.volume, cmd.duration_ms);
	}

	LOG_INF("fix %.6f,%.6f acc=%.1fm sats=%u state=%s margin=%.1fm%s%s cue=%s vol=%u",
		f->lat, f->lon, (double)f->accuracy, f->sats_in_fix,
		geofence_state_str(r.state), r.margin_m, r.degraded ? " (degraded)" : "",
		cue.armed ? "" : " (unarmed)", cmd.active ? "on" : "off", cmd.volume);

	if (r.changed) {
		LOG_INF("event: state -> %s", geofence_state_str(r.state));
	}
}

int main(void)
{
	struct fix f;

	LOG_INF("OpenCollar V0 starting");

	cue_init(&cue, &cue_cfg);

	if (apply_boundary(boundary_vertices, ARRAY_LEN(boundary_vertices),
			   BOUNDARY_VERSION) != 0) {
		LOG_ERR("Invalid boundary");
		return 0;
	}
	LOG_INF("Boundary v%u loaded: %u vertices", BOUNDARY_VERSION,
		(unsigned)ARRAY_LEN(boundary_vertices));

	if (buzzer_init() == 0) {
		/* Short chirp so you know the cue path works at boot */
		buzzer_play(cue_cfg.warn_freq_hz, 2, 150);
	}

	if (gnss_start() != 0) {
		return 0;
	}
	LOG_INF("GNSS started");

	while (true) {
		k_msgq_get(&fix_q, &f, K_FOREVER);
		handle_fix(&f);
	}

	return 0;
}
