/* SPDX-License-Identifier: Apache-2.0 */
/* MAX17260 on the carrier's I2C bus (rook_battery.h). Without
 * CONFIG_ROOK_BATTERY_MAX17260 every read is -ENODEV. */
#include "rook_battery.h"

#include <errno.h>
#include <zephyr/device.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/byteorder.h>

/* The carrier's main I2C bus. TODO: confirm once the carrier overlay exists;
 * i2c2 is the Connect Kit's Qwiic bus (buzzer) today. */
#define ROOK_BATTERY_BUS DT_NODELABEL(i2c2)

#if defined(CONFIG_ROOK_BATTERY_MAX17260) && DT_NODE_HAS_STATUS(ROOK_BATTERY_BUS, okay)
static const struct device *bus = DEVICE_DT_GET(ROOK_BATTERY_BUS);

static int rd(uint8_t reg, uint16_t *v)
{
	uint8_t b[2];
	int err = i2c_write_read(bus, MAX17260_ADDR, &reg, 1, b, 2);

	*v = sys_get_le16(b);
	return err;
}

int rook_battery_init(void)
{
	return device_is_ready(bus) ? 0 : -ENODEV;
}

int rook_battery_read(struct rook_battery *out)
{
	uint16_t soc, v, i;

	if (!device_is_ready(bus) || rd(MAX17260_REG_REPSOC, &soc) || rd(MAX17260_REG_VCELL, &v) ||
	    rd(MAX17260_REG_CURRENT, &i)) {
		return -ENODEV;
	}
	out->soc = max17260_soc(soc);
	out->voltage_v = max17260_vcell(v);
	out->current_ma = max17260_current_ma(i, ROOK_RSENSE_MOHM);
	out->charging = out->current_ma > 5.0f;
	return 0;
}
#else
#if defined(CONFIG_ROOK_BATTERY_MAX17260)
#error "CONFIG_ROOK_BATTERY_MAX17260 needs the carrier I2C bus enabled in devicetree"
#endif
int rook_battery_init(void)
{
	return -ENODEV;
}

int rook_battery_read(struct rook_battery *out)
{
	(void)out;
	return -ENODEV;
}
#endif
