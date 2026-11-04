/* SPDX-License-Identifier: Apache-2.0 */
/*
 * The server's root CA, embedded at build time (CONFIG_ROOK_LTE_CA_PEM) and
 * written into the modem's sec tag (CONFIG_ROOK_LTE_SEC_TAG) before the
 * first attach when it is missing or different. The decision is plain C.
 */
#ifndef ROOK_CA_H
#define ROOK_CA_H

#include <stdbool.h>

enum rook_ca_act {
	ROOK_CA_KEEP,  /* the tag already holds it (or can't be compared but holds one) */
	ROOK_CA_WRITE, /* missing or different */
	ROOK_CA_FAIL,  /* the modem refused (e.g. -EACCES); leave it, report */
};

/* cmp: modem_key_mgmt_cmp's result (0 same, 1 different, -errno);
 * exists: what modem_key_mgmt_exists said, used only when cmp is -ENOBUFS */
enum rook_ca_act rook_ca_action(int cmp, bool exists);

/* Write the embedded CA if needed. 0, or a negative errno. Modem offline
 * (CFUN=0 or 4). A no-op without CONFIG_ROOK_LTE_CA_PEM. */
int rook_ca_provision(void);

#endif
