/*
 * Register map from SparkFun's MIT-licensed Qwiic Buzzer Arduino library.
 * Multi-byte values are big-endian.
 */
#include "buzzer.h"

#include <zephyr/device.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(buzzer, LOG_LEVEL_INF);

#define BUZZER_ADDR 0x34
#define BUZZER_ID   0x5E

#define REG_ID        0x00
#define REG_FREQ_MSB  0x03 /* followed by FREQ_LSB, VOLUME, DURATION_MSB, DURATION_LSB */
#define REG_ACTIVE    0x08

static const struct device *const i2c = DEVICE_DT_GET(DT_NODELABEL(i2c2));
static bool present;

int buzzer_init(void)
{
	uint8_t id = 0;
	int err;

	if (!device_is_ready(i2c)) {
		LOG_ERR("I2C bus not ready");
		return -ENODEV;
	}

	err = i2c_reg_read_byte(i2c, BUZZER_ADDR, REG_ID, &id);
	if (err) {
		LOG_WRN("Buzzer not found at 0x%02x (%d)", BUZZER_ADDR, err);
		return err;
	}
	if (id != BUZZER_ID) {
		LOG_WRN("Unexpected buzzer ID 0x%02x", id);
		return -EIO;
	}

	present = true;
	LOG_INF("Buzzer ready");
	return 0;
}

int buzzer_play(uint16_t freq_hz, uint8_t volume, uint16_t duration_ms)
{
	if (!present) {
		return -ENODEV;
	}

	uint8_t settings[] = {
		REG_FREQ_MSB,
		freq_hz >> 8, freq_hz & 0xff,
		volume > 4 ? 4 : volume,
		duration_ms >> 8, duration_ms & 0xff,
	};
	int err = i2c_write(i2c, settings, sizeof(settings), BUZZER_ADDR);

	if (err) {
		return err;
	}

	return i2c_reg_write_byte(i2c, BUZZER_ADDR, REG_ACTIVE, 1);
}

int buzzer_stop(void)
{
	if (!present) {
		return -ENODEV;
	}

	return i2c_reg_write_byte(i2c, BUZZER_ADDR, REG_ACTIVE, 0);
}
