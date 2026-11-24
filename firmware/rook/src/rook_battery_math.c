/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_battery.h"

float max17260_soc(uint16_t repsoc)
{
	float s = (float)repsoc / 256.0f / 100.0f;

	return s > 1.0f ? 1.0f : s;
}

float max17260_vcell(uint16_t vcell)
{
	return (float)vcell * 78.125e-6f;
}

float max17260_current_ma(uint16_t raw, uint32_t rsense_mohm)
{
	/* 1.5625 uV / Rsense; uV / mOhm = mA */
	return (float)(int16_t)raw * 1.5625f / (float)rsense_mohm;
}
