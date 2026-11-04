/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#include "test.h"

#include "gnss_ubx.h"

int main(void)
{
	struct gnss_ubx_uart u;
	/* Valid RMC: Nashville-ish; checksum computed for this sentence. */
	const char *rmc =
		"$GPRMC,123519,A,3600.0300,N,08600.0300,W,0.0,0.0,030126,,,A*62\r\n";
	const char *bad = "$GPRMC,123519,V,3600.0300,N,08600.0300,W,0.0,0.0,030126,,,A*75\r\n";

	gnss_ubx_init(&u);
	CHECK(gnss_ubx_feed(&u, (const uint8_t *)rmc, strlen(rmc)) >= 1);
	CHECK(u.last.valid);
	CHECK_NEAR(u.last.lat, 36.0005, 0.001);
	CHECK_NEAR(u.last.lon, -86.0005, 0.001);

	gnss_ubx_init(&u);
	CHECK(gnss_ubx_feed(&u, (const uint8_t *)bad, strlen(bad)) >= 0);
	/* V = void fix → invalid after a checksum-ok parse */
	if (u.have_fix) {
		CHECK(!u.last.valid);
	}

	return test_done("ubx_nmea");
}
