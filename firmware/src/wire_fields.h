/*
 * Wire field names and tokens for rearm / welfare / report telemetry (v1 JSON).
 *
 * Keep every rearm, welfare and report-telemetry key here so a protocol-record
 * rename (op-ingest / op-protocol) is one edit. v2 will carry the same fields
 * as signed CBOR (COSE) where applicable; names stay stable.
 */
#ifndef OPENCOLLAR_WIRE_FIELDS_H
#define OPENCOLLAR_WIRE_FIELDS_H

/* Command type */
#define OC_TYPE_REARM "rearm"

/* Signed rearm command keys */
#define OC_FIELD_TYPE "type"
#define OC_FIELD_COMMAND_ID "command_id"
#define OC_FIELD_COLLAR_ID "collar_id"
#define OC_FIELD_HERD_ID "herd_id"
#define OC_FIELD_REARM_SEQ "rearm_seq"
#define OC_FIELD_ISSUED_AT "issued_at"
#define OC_FIELD_EXPIRES_AT "expires_at"
#define OC_FIELD_SHUTOFF_AT "shutoff_at"
#define OC_FIELD_REASON_CODE "reason_code"
#define OC_FIELD_SIG "sig"

/* Report welfare block */
#define OC_FIELD_WELFARE "welfare"
#define OC_FIELD_ENFORCEMENT "enforcement"
#define OC_FIELD_ESCAPE_CYCLES "escape_cycles"
#define OC_FIELD_WELFARE_EVENTS "welfare_events"
#define OC_FIELD_KIND "kind"
#define OC_FIELD_AT "at"
#define OC_FIELD_BY "by"
#define OC_FIELD_OUTSIDE_CUES "outside_cues"

/* Report telemetry (read-only; farmer app). Rename here if the server record differs. */
#define OC_FIELD_BATTERY "battery"
#define OC_FIELD_HEALTH "health"
#define OC_FIELD_LAST_CUE_AT "last_cue_at"
#define OC_FIELD_CELL "cell"
#define OC_FIELD_RSRP_DBM "rsrp_dbm" /* nested: health.cell.rsrp_dbm (v1); not flat health.rsrp_dbm */
#define OC_FIELD_FIXES "fixes"
#define OC_FIELD_POINT "point"
#define OC_FIELD_ACCURACY_M "accuracy_m"
#define OC_FIELD_SATS "sats"
#define OC_FIELD_CN0 "cn0"
#define OC_FIELD_HDOP "hdop" /* existing v1 fixes[].hdop */

/* Cap advertised in device.caps */
#define OC_CAP_REARM "rearm"

/* enforcement values */
#define OC_ENFORCEMENT_ON "on"
#define OC_ENFORCEMENT_OFF "off"

/* enforcement_resumed.by */
#define OC_BY_SERIAL "serial"
#define OC_BY_SERVER "server"

/* reason_code max length (token, not free text) */
#define OC_REASON_CODE_MAX 32

#endif
