/*
 * Provisioning (protocol v1 §3.9). Plain C over store.h, host-testable.
 *
 * The payload is the QR text printed on a collar's card:
 *   {"v":1,"c":"<collar id>","h":"<herd id>","k":"<collar key>",
 *    "e":"<base>/collar/v1","s":"<server public key, base64>"}
 * It arrives as one console line, `provision <payload>` (a handheld scanner
 * in keyboard mode types it into a serial terminal). Checked in this order,
 * each failure being the reply `error <code>`:
 *   bad_json        not a flat JSON object (the command scanner's rules)
 *   bad_version     v is not 1
 *   bad_collar_id   c is not a string of 1-64 bytes
 *   bad_herd_id     h is not a string of 1-64 bytes
 *   bad_key         k is not 16-128 printable ASCII characters
 *   bad_endpoint    e is not https:// or is over 256 bytes
 *   bad_server_key  s is not base64 of 32 bytes
 * Unknown keys are ignored. The payload is stored as sent in NVS id 1 and
 * checked again at every boot.
 */
#ifndef OPENCOLLAR_PROVISION_H
#define OPENCOLLAR_PROVISION_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "protocol.h"

#define PROVISION_MAX_BYTES 1024
#define PROVISION_KEY_MIN 16
#define PROVISION_KEY_MAX 128

enum prov_error {
	PROV_OK = 0,
	PROV_BAD_JSON,
	PROV_BAD_VERSION,
	PROV_BAD_COLLAR_ID,
	PROV_BAD_HERD_ID,
	PROV_BAD_KEY,
	PROV_BAD_ENDPOINT,
	PROV_BAD_SERVER_KEY,
	PROV_STORE_FAILED,
};

const char *prov_error_str(enum prov_error e);

struct provision {
	bool ok; /* Provisioned */
	struct proto_id collar_id;
	struct proto_id herd_id;
	char key[PROVISION_KEY_MAX + 1];
	char endpoint[PROTO_MAX_ENDPOINT_BYTES + 1];
	uint8_t server_key[32];
};

/* Check a payload; out is filled (ok = true) only when it passes */
enum prov_error provision_parse(const char *json, size_t len, struct provision *out);

/* From NVS id 1: out->ok is false when there is none or it doesn't pass */
void provision_load(struct provision *out);

/* Store a payload that passed provision_parse */
int provision_save(const char *json, size_t len);

#endif
