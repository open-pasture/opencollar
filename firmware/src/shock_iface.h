/*
 * Shock / pulse module — names and states only.
 *
 * Reservation: docs/SHOCK-MODULE-INTERFACE.md, protocol/registry.md.
 * This header must not grow functions that drive any output. Record H
 * (welfare-reviewer question) still blocks any live use. Default is off;
 * not_fitted / unknown means no path may drive HV.
 */
#ifndef OPENCOLLAR_SHOCK_IFACE_H
#define OPENCOLLAR_SHOCK_IFACE_H

/* Firmware-internal / registry module states. Wire: emit health.module only
 * when fitted; omit the block when not_fitted (servers must not treat absence
 * as ok). Do not reuse the v2 fence "armed" status bit for the module. */
enum shock_module_state {
	SHOCK_NOT_FITTED = 0,
	SHOCK_FITTED_DISABLED = 1,
	SHOCK_FITTED_READY = 2,
	SHOCK_FAULT = 3,
	SHOCK_KILLED = 4,
};

/* Proposed fault names; any fault keeps HV off until a person re-arms. */
enum shock_fault {
	SHOCK_FAULT_NONE = 0,
	SHOCK_FAULT_OPEN_ELECTRODE = 1,
	SHOCK_FAULT_SHORT = 2,
	SHOCK_FAULT_OVER_CURRENT = 3,
	SHOCK_FAULT_NO_CONTACT = 4,
	SHOCK_FAULT_OVER_TEMP = 5,
	SHOCK_FAULT_BAD_ID = 6,
};

/* Stable wire / registry string names (v1 JSON style). */
#define SHOCK_CAP_NAME "shock_module"
#define SHOCK_CUE_KIND_PULSE "pulse"
#define SHOCK_REPORT_HEALTH_MODULE "module"
#define SHOCK_REPORT_PRESENT "present"
#define SHOCK_REPORT_HW_REV "hw_rev"
#define SHOCK_REPORT_STATE "state"
#define SHOCK_REPORT_FAULT "fault"

#define SHOCK_STATE_NAME_NOT_FITTED "not_fitted"
#define SHOCK_STATE_NAME_FITTED_DISABLED "fitted_disabled"
#define SHOCK_STATE_NAME_FITTED_READY "fitted_ready"
#define SHOCK_STATE_NAME_FAULT "fault"
#define SHOCK_STATE_NAME_KILLED "killed"

#define SHOCK_FAULT_NAME_OPEN_ELECTRODE "open_electrode"
#define SHOCK_FAULT_NAME_SHORT "short"
#define SHOCK_FAULT_NAME_OVER_CURRENT "over_current"
#define SHOCK_FAULT_NAME_NO_CONTACT "no_contact"
#define SHOCK_FAULT_NAME_OVER_TEMP "over_temp"
#define SHOCK_FAULT_NAME_BAD_ID "bad_id"

/* Logical connector nets (MCU pin numbers TBD; see interface doc). */
#define SHOCK_NET_SENSE "SENSE"
#define SHOCK_NET_I2C_SDA "I2C_SDA"
#define SHOCK_NET_I2C_SCL "I2C_SCL"
#define SHOCK_NET_HV_EN "HV_EN"
#define SHOCK_NET_KILL "KILL"
#define SHOCK_NET_FAULT "FAULT"
#define SHOCK_NET_GND "GND"
#define SHOCK_NET_BAT "BAT"
#define SHOCK_NET_GATE_LATCH "GATE_LATCH"
#define SHOCK_NET_KILL_SENSE "KILL_SENSE"

#endif
