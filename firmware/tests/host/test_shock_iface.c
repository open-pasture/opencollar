/*
 * Stability of shock_iface.h enum values and field-name constants.
 * No driver code: the header must not grow functions that assert HV.
 */
#include "test.h"

#include "../../src/shock_iface.h"

static void test_state_values_stable(void)
{
	CHECK(SHOCK_NOT_FITTED == 0);
	CHECK(SHOCK_FITTED_DISABLED == 1);
	CHECK(SHOCK_FITTED_READY == 2);
	CHECK(SHOCK_FAULT == 3);
	CHECK(SHOCK_KILLED == 4);
}

static void test_fault_values_stable(void)
{
	CHECK(SHOCK_FAULT_NONE == 0);
	CHECK(SHOCK_FAULT_OPEN_ELECTRODE == 1);
	CHECK(SHOCK_FAULT_SHORT == 2);
	CHECK(SHOCK_FAULT_OVER_CURRENT == 3);
	CHECK(SHOCK_FAULT_NO_CONTACT == 4);
	CHECK(SHOCK_FAULT_OVER_TEMP == 5);
	CHECK(SHOCK_FAULT_BAD_ID == 6);
}

static void test_field_names_stable(void)
{
	CHECK(strcmp(SHOCK_CAP_NAME, "shock_module") == 0);
	CHECK(strcmp(SHOCK_PULSE_GRANT_NAME, "pulse_grant") == 0);
	CHECK(strcmp(SHOCK_CUE_KIND_PULSE, "pulse") == 0);
	CHECK(strcmp(SHOCK_REPORT_HEALTH_MODULE, "module") == 0);
	CHECK(strcmp(SHOCK_REPORT_HW_REV, "hw_rev") == 0);
	CHECK(strcmp(SHOCK_REPORT_STATE, "state") == 0);
	CHECK(strcmp(SHOCK_REPORT_FAULT, "fault") == 0);

	CHECK(strcmp(SHOCK_STATE_NAME_NOT_FITTED, "not_fitted") == 0);
	CHECK(strcmp(SHOCK_STATE_NAME_FITTED_DISABLED, "fitted_disabled") == 0);
	CHECK(strcmp(SHOCK_STATE_NAME_FITTED_READY, "fitted_ready") == 0);
	CHECK(strcmp(SHOCK_STATE_NAME_FAULT, "fault") == 0);
	CHECK(strcmp(SHOCK_STATE_NAME_KILLED, "killed") == 0);

	CHECK(strcmp(SHOCK_FAULT_NAME_OPEN_ELECTRODE, "open_electrode") == 0);
	CHECK(strcmp(SHOCK_FAULT_NAME_SHORT, "short") == 0);
	CHECK(strcmp(SHOCK_FAULT_NAME_OVER_CURRENT, "over_current") == 0);
	CHECK(strcmp(SHOCK_FAULT_NAME_NO_CONTACT, "no_contact") == 0);
	CHECK(strcmp(SHOCK_FAULT_NAME_OVER_TEMP, "over_temp") == 0);
	CHECK(strcmp(SHOCK_FAULT_NAME_BAD_ID, "bad_id") == 0);
}

static void test_net_names_stable(void)
{
	CHECK(strcmp(SHOCK_NET_SENSE, "SENSE") == 0);
	CHECK(strcmp(SHOCK_NET_I2C_SDA, "I2C_SDA") == 0);
	CHECK(strcmp(SHOCK_NET_I2C_SCL, "I2C_SCL") == 0);
	CHECK(strcmp(SHOCK_NET_HV_EN, "HV_EN") == 0);
	CHECK(strcmp(SHOCK_NET_KILL, "KILL") == 0);
	CHECK(strcmp(SHOCK_NET_FAULT, "FAULT") == 0);
	CHECK(strcmp(SHOCK_NET_GND, "GND") == 0);
	CHECK(strcmp(SHOCK_NET_BAT, "BAT") == 0);
	CHECK(strcmp(SHOCK_NET_GATE_LATCH, "GATE_LATCH") == 0);
	CHECK(strcmp(SHOCK_NET_KILL_SENSE, "KILL_SENSE") == 0);
}

int main(void)
{
	test_state_values_stable();
	test_fault_values_stable();
	test_field_names_stable();
	test_net_names_stable();
	return test_done("shock_iface");
}
