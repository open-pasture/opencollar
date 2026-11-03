/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Minimal NMEA RMC/GGA parser + UBX frame sync. Written from the public
 * u-blox / NMEA descriptions; not copied from any GPL project.
 */
#include "gnss_ubx.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void gnss_ubx_init(struct gnss_ubx_uart *u)
{
	memset(u, 0, sizeof(*u));
}

static int nmea_checksum_ok(const char *s)
{
	const char *star;
	unsigned int want;
	unsigned char cs = 0;

	if (s[0] != '$') {
		return 0;
	}
	star = strchr(s + 1, '*');
	if (!star || star[1] == '\0' || star[2] == '\0') {
		return 0;
	}
	for (const char *p = s + 1; p < star; p++) {
		cs ^= (unsigned char)*p;
	}
	if (sscanf(star + 1, "%2x", &want) != 1) {
		return 0;
	}
	return cs == (unsigned char)want;
}

static const char *nmea_field(const char *s, int idx)
{
	const char *p = s;
	int i = 0;

	while (*p && *p != '*') {
		if (i == idx) {
			return p;
		}
		if (*p == ',') {
			i++;
		}
		p++;
	}
	return NULL;
}

static double nmea_deg(const char *field, char hemi)
{
	double raw, deg, minutes;

	if (!field || *field == ',' || *field == '\0') {
		return 0.0;
	}
	raw = atof(field);
	deg = (int)(raw / 100.0);
	minutes = raw - deg * 100.0;
	deg += minutes / 60.0;
	if (hemi == 'S' || hemi == 'W') {
		deg = -deg;
	}
	return deg;
}

static void try_nmea_line(struct gnss_ubx_uart *u, char *line)
{
	const char *lat_s, *ns, *lon_s, *ew, *status, *qual;
	char hemi_ns, hemi_ew;

	if (!nmea_checksum_ok(line)) {
		return;
	}
	if (strncmp(line, "$GPRMC", 6) == 0 || strncmp(line, "$GNRMC", 6) == 0) {
		status = nmea_field(line, 2);
		lat_s = nmea_field(line, 3);
		ns = nmea_field(line, 4);
		lon_s = nmea_field(line, 5);
		ew = nmea_field(line, 6);
		if (!status || status[0] != 'A') {
			u->last.valid = false;
			u->have_fix = true;
			return;
		}
		hemi_ns = ns ? ns[0] : 'N';
		hemi_ew = ew ? ew[0] : 'E';
		u->last.lat = nmea_deg(lat_s, hemi_ns);
		u->last.lon = nmea_deg(lon_s, hemi_ew);
		u->last.valid = true;
		u->last.accuracy_m = 5.0; /* RMC has no accuracy; GGA/UBX refine */
		u->have_fix = true;
		return;
	}
	if (strncmp(line, "$GPGGA", 6) == 0 || strncmp(line, "$GNGGA", 6) == 0) {
		qual = nmea_field(line, 6);
		lat_s = nmea_field(line, 2);
		ns = nmea_field(line, 3);
		lon_s = nmea_field(line, 4);
		ew = nmea_field(line, 5);
		if (!qual || qual[0] == '0') {
			u->last.valid = false;
			u->have_fix = true;
			return;
		}
		hemi_ns = ns ? ns[0] : 'N';
		hemi_ew = ew ? ew[0] : 'E';
		u->last.lat = nmea_deg(lat_s, hemi_ns);
		u->last.lon = nmea_deg(lon_s, hemi_ew);
		u->last.valid = true;
		u->have_fix = true;
	}
}

int gnss_ubx_feed(struct gnss_ubx_uart *u, const uint8_t *data, size_t len)
{
	size_t i;
	int fixes = 0;

	for (i = 0; i < len; i++) {
		if (u->rx_len + 1 >= GNSS_UBX_RX_CAP) {
			u->rx_len = 0;
		}
		u->rx[u->rx_len++] = data[i];
		if (data[i] == '\n' && u->rx_len >= 2) {
			char line[GNSS_UBX_RX_CAP];
			size_t n = u->rx_len;

			if (n >= sizeof(line)) {
				n = sizeof(line) - 1;
			}
			memcpy(line, u->rx, n);
			line[n] = '\0';
			/* Trim CR */
			if (n > 0 && line[n - 1] == '\n') {
				line[n - 1] = '\0';
			}
			if (n > 1 && line[n - 2] == '\r') {
				line[n - 2] = '\0';
			}
			u->have_fix = false;
			try_nmea_line(u, line);
			if (u->have_fix) {
				fixes++;
			}
			u->rx_len = 0;
		}
		/* UBX sync: 0xB5 0x62 — length framing deferred; host uses NMEA. */
	}
	return fixes;
}

static int ubx_init(void *ctx)
{
	struct gnss_ubx_uart *u = ctx;

	u->rx_len = 0;
	u->have_fix = false;
	memset(&u->last, 0, sizeof(u->last));
	return 0;
}

static int ubx_poll(void *ctx, int64_t now_ms, struct gnss_fix *fix)
{
	struct gnss_ubx_uart *u = ctx;
	uint8_t buf[128];
	int n;

	(void)now_ms;
	if (u->uart_read) {
		n = u->uart_read(u->io, buf, sizeof(buf));
		if (n > 0) {
			gnss_ubx_feed(u, buf, (size_t)n);
		}
	}
	*fix = u->last;
	if (!u->have_fix) {
		fix->valid = false;
	}
	return 0;
}

static int ubx_sleep(void *ctx)
{
	(void)ctx;
	return 0;
}

static int ubx_wake(void *ctx)
{
	(void)ctx;
	return 0;
}

static const struct gnss_ops UBX_OPS = {
	.init = ubx_init,
	.poll = ubx_poll,
	.sleep = ubx_sleep,
	.wake = ubx_wake,
};

const struct gnss_ops *gnss_ubx_ops(void)
{
	return &UBX_OPS;
}
