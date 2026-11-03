/*
 * Zephyr SX126x platform binder.
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RHAL_ZEPHYR_H
#define OPENCOLLAR_RHAL_ZEPHYR_H

#include "radio_hal.h"

#ifdef __cplusplus
extern "C" {
#endif

struct device;

int rhal_zephyr_platform(struct rhal_platform *plat, const struct device *dev);

#ifdef __cplusplus
}
#endif

#endif
