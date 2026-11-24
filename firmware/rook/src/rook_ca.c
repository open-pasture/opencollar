/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_ca.h"

#include <errno.h>

enum rook_ca_act rook_ca_action(int cmp, bool exists)
{
	if (cmp == 0) {
		return ROOK_CA_KEEP;
	}
	if (cmp == 1 || cmp == -ENOENT) {
		return ROOK_CA_WRITE;
	}
	if (cmp == -ENOBUFS) {
		/* Too big for the library's compare buffer: don't rewrite flash every boot */
		return exists ? ROOK_CA_KEEP : ROOK_CA_WRITE;
	}
	return ROOK_CA_FAIL;
}

#ifdef __ZEPHYR__
#include <string.h>
#include <zephyr/logging/log.h>
#include <modem/modem_key_mgmt.h>

LOG_MODULE_DECLARE(rook_lte);

#ifdef ROOK_CA_EMBEDDED
static const char ca_pem[] = {
#include "rook_ca.pem.inc"
	0x00};
#endif

int rook_ca_provision(void)
{
#ifdef ROOK_CA_EMBEDDED
	const size_t len = strlen(ca_pem);
	bool exists = false;
	int cmp, err;

	cmp = modem_key_mgmt_cmp(CONFIG_ROOK_LTE_SEC_TAG, MODEM_KEY_MGMT_CRED_TYPE_CA_CHAIN,
				 ca_pem, len);
	if (cmp == -ENOBUFS) {
		modem_key_mgmt_exists(CONFIG_ROOK_LTE_SEC_TAG, MODEM_KEY_MGMT_CRED_TYPE_CA_CHAIN,
				      &exists);
	}
	switch (rook_ca_action(cmp, exists)) {
	case ROOK_CA_KEEP:
		LOG_INF("CA in sec tag %d: present", CONFIG_ROOK_LTE_SEC_TAG);
		return 0;
	case ROOK_CA_WRITE:
		err = modem_key_mgmt_write(CONFIG_ROOK_LTE_SEC_TAG,
					   MODEM_KEY_MGMT_CRED_TYPE_CA_CHAIN, ca_pem, len);
		LOG_INF("CA in sec tag %d: written (%u B) -> %d", CONFIG_ROOK_LTE_SEC_TAG,
			(unsigned)len, err);
		return err;
	default:
		LOG_WRN("CA in sec tag %d: compare failed %d", CONFIG_ROOK_LTE_SEC_TAG, cmp);
		return cmp;
	}
#else
	return 0;
#endif
}
#endif
