/*
 * Collar configuration (protocol v1 §3.4): the signed command that sets the
 * collar's herd, endpoint and report cadence. It rides inside the report
 * response. Plain C, time passed in, persistence through store.h (NVS id 3).
 *
 * - Scanned, signed and canonicalized exactly like boundary commands.
 * - Checks in order: ids (bad_json), wrong_collar, stale (version at or
 *   below the one held), bad_config (an interval outside 10-3600 s,
 *   fast_until without both fast intervals, an endpoint that isn't https://
 *   or is over 256 bytes).
 * - herd_id replaces the provisioning herd for wrong_herd checks.
 * - fast_report_s/fast_poll_s apply until fast_until (GNSS time), then the
 *   base cadence returns without another command. With no GNSS time since
 *   boot the base cadence applies.
 * - endpoint: absent keeps the current one. A new one is tried from the next
 *   report; the first successful report there makes it the endpoint, and if
 *   it has failed for 24 h the collar goes back to the previous one, so a bad
 *   URL never strands it.
 * - A rejected config is kept (version and code) to be reported once as
 *   device.config_reject.
 */
#ifndef OPENCOLLAR_CONFIG_H
#define OPENCOLLAR_CONFIG_H

#include <stdbool.h>
#include <stdint.h>

#include "protocol.h"

#define CONFIG_MIN_INTERVAL_S 10
#define CONFIG_MAX_INTERVAL_S 3600
#define CONFIG_DEFAULT_INTERVAL_S 60
#define CONFIG_ENDPOINT_FALLBACK_S (24 * 3600)

struct config_cmd {
	struct proto_id command_id;
	struct proto_id collar_id;
	uint32_t version;
	bool has_herd;
	struct proto_id herd_id;
	bool has_endpoint;
	size_t endpoint_len; /* Full length, even when over the limit */
	char endpoint[PROTO_MAX_ENDPOINT_BYTES + 1];
	uint32_t report_s, poll_s;
	bool has_fast_report, has_fast_poll;
	uint32_t fast_report_s, fast_poll_s;
	bool has_fast_until;
	int64_t fast_until;
};

/* Scan, verify and read (bad_json, too_large, bad_sig) */
enum reject_code config_parse(const char *wire, size_t len, const uint8_t public_key[32],
			      struct config_cmd *out);
/* wrong_collar, stale, bad_config */
enum reject_code config_check(const struct config_cmd *c, const struct proto_id *collar_id,
			      bool has_held, uint32_t held_version);

struct config {
	bool has; /* A config has been applied */
	uint32_t version;
	bool has_herd;
	struct proto_id herd;
	uint32_t report_s, poll_s;
	bool has_fast;
	uint32_t fast_report_s, fast_poll_s;
	bool has_fast_until;
	int64_t fast_until;

	/* Endpoint: the one confirmed by a successful report, and one on trial */
	bool has_endpoint;
	char endpoint[PROTO_MAX_ENDPOINT_BYTES + 1];
	bool trying;
	char trial[PROTO_MAX_ENDPOINT_BYTES + 1];
	bool has_trial_since;
	int64_t trial_since;

	/* The last rejected config, until reported */
	bool has_reject;
	uint32_t reject_version;
	enum reject_code reject_code;

	uint32_t store_errors;
};

/* No config: base cadence 60 s, the provisioning endpoint and herd */
void config_init(struct config *c);
void config_load(struct config *c);
void config_wipe(struct config *c);

/*
 * A config from a report response. has_now/now: GNSS time. base_endpoint:
 * the provisioning endpoint. Returns REJECT_NONE when it was applied.
 */
enum reject_code config_receive(struct config *c, const char *wire, size_t len,
				const uint8_t public_key[32], const struct proto_id *collar_id,
				const char *base_endpoint, bool has_now, int64_t now);

/* The URL to report to now */
const char *config_endpoint(const struct config *c, const char *base_endpoint);

/* How the last report went. has_now/now: GNSS time. */
void config_report_result(struct config *c, bool ok, bool has_now, int64_t now);

/* Report and poll intervals at GNSS time now */
void config_cadence(const struct config *c, bool has_now, int64_t now, uint32_t *report_s,
		    uint32_t *poll_s);

#endif
