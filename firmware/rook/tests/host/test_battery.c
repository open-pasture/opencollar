/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_battery.h"
#include "test.h"

int main(void)
{
	CHECK_NEAR(max17260_soc(0x5100), 0.81, 1e-6);   /* 81 % */
	CHECK_NEAR(max17260_soc(0xffff), 1.0, 1e-6);
	CHECK_NEAR(max17260_vcell(42368), 3.31, 1e-6);  /* 42368 * 78.125 uV */
	CHECK_NEAR(max17260_current_ma(640, 10), 100.0, 1e-4);
	CHECK_NEAR(max17260_current_ma((uint16_t)-640, 10), -100.0, 1e-4);
	return test_done("rook battery");
}
