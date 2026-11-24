/* SPDX-License-Identifier: Apache-2.0 */
/*
 * Battery reading behind one small interface. Backend for the alpha collar:
 * the carrier board's MAX17260 fuel gauge (U6, rev A3, high-side 10 mOhm
 * sense R24, main I2C bus at 0x36, ALRT on P0.00), per
 * docs/CARRIER-EXPLAINED.md and hardware/ (carrier netlist, rev A3). The bare
 * Connect Kit has no gauge and no battery ADC path, so without the carrier
 * rook_battery_read() returns -ENODEV and reports simply omit battery.
 *
 * The register maths is plain C (host-tested); the I2C transport is in
 * rook_battery_max17260.c (Zephyr).
 */
#ifndef ROOK_BATTERY_H
#define ROOK_BATTERY_H

#include <stdbool.h>
#include <stdint.h>

struct rook_battery {
	float soc;        /* 0..1 (RepSOC) */
	float voltage_v;  /* VCell */
	float current_ma; /* + charging, - discharging */
	bool charging;
};

int rook_battery_init(void);
int rook_battery_read(struct rook_battery *out);

/* MAX17260 register maths ([MAX] Table 1/9) */
#define MAX17260_ADDR 0x36
#define MAX17260_REG_REPSOC 0x06
#define MAX17260_REG_VCELL 0x09
#define MAX17260_REG_CURRENT 0x0A
#define ROOK_RSENSE_MOHM 10

float max17260_soc(uint16_t repsoc);      /* 1/256 % per LSB */
float max17260_vcell(uint16_t vcell);     /* 78.125 uV per LSB */
float max17260_current_ma(uint16_t raw, uint32_t rsense_mohm); /* 1.5625 uV/Rsense */

#endif
