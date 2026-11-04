/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_state.h"

#include <string.h>

void rook_state_take(const struct app *a, struct rook_dev_state *o)
{
	const struct slots *s = &a->slots;
	int64_t now = 0;
	bool has_now;
	uint32_t poll_s;

	memset(o, 0, sizeof(*o));
	o->provisioned = a->prov.ok;
	o->limits = s->limits;
	for (int i = 0; i < s->n && i < SLOT_IDS; i++) {
		o->slot[i].version = s->s[i].version;
		o->slot[i].applied = (s->s[i].flags & SLOT_F_APPLIED) != 0;
		o->slot[i].has_effective_at = (s->s[i].flags & SLOT_F_EFFECTIVE) != 0;
		o->slot[i].effective_at = s->s[i].effective_at;
		o->n_slots++;
	}
	o->have = slots_have(s);
	o->free = slots_free(s);
	o->has_free_bytes = slots_free_bytes(s, &o->free_bytes);
	o->has_config = a->cfg.has;
	o->config_version = a->cfg.version;
	o->has_config_reject = a->cfg.has_reject;
	o->config_reject_version = a->cfg.reject_version;
	o->config_reject_code = (uint8_t)a->cfg.reject_code;
	if (a->prov.ok) {
		const char *ep = config_endpoint(&a->cfg, a->prov.endpoint);

		strncpy(o->endpoint, ep, sizeof(o->endpoint) - 1);
	}
	has_now = app_now(a, a->now_ms, &now);
	config_cadence(&a->cfg, has_now, now, &o->report_s, &poll_s);
}
