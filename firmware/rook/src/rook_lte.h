/* SPDX-License-Identifier: Apache-2.0 */
/*
 * The Rook's LTE-M reporter (Zephyr/NCS). A thread that:
 *  - attaches to LTE-M (PSM requested, APN from Kconfig when set),
 *  - POSTs <endpoint>/report with queued fixes, fence state and battery,
 *  - GETs <endpoint>/boundary?have=N and hands a downloaded command to the
 *    main thread (Ed25519 runs there), then POSTs <endpoint>/ack,
 *  - retries per protocol/v2/http.md §5/§8 (rook_backoff.c).
 * Endpoint and bearer key come from provisioning; Kconfig overrides exist
 * for the mock server. TLS is the modem's (sec tag CONFIG_ROOK_LTE_SEC_TAG).
 *
 * main.c calls: rook_lte_start() once after app_boot(), rook_lte_on_fix()
 * per fix, and rook_lte_service() when rook_lte_signal() is raised.
 */
#ifndef ROOK_LTE_H
#define ROOK_LTE_H

#include <zephyr/kernel.h>

#include "app.h"

int rook_lte_start(const struct app *a);
void rook_lte_on_fix(const struct app *a, const struct app_fix_in *in,
		     const struct app_fix_out *out, uint8_t sats);
struct k_poll_signal *rook_lte_signal(void);
/* Main thread: verify and store a downloaded boundary, if one is waiting */
void rook_lte_service(struct app *a);

#endif
