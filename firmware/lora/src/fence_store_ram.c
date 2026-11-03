#include "opencollar/fence_store.h"

#include <string.h>

static int ram_get_hwm(oc_fh_store_t *s, uint32_t *out_seq)
{
	oc_fh_store_ram_t *r = (oc_fh_store_ram_t *)s->ctx;
	if (!r || !out_seq) {
		return -1;
	}
	*out_seq = r->hwm;
	return 0;
}

static int ram_set_hwm(oc_fh_store_t *s, uint32_t seq)
{
	oc_fh_store_ram_t *r = (oc_fh_store_ram_t *)s->ctx;
	if (!r) {
		return -1;
	}
	if (seq > r->hwm) {
		r->hwm = seq;
	}
	return 0;
}

static int ram_save(oc_fh_store_t *s, const oc_fh_freshness_t *fr, const uint8_t *payload,
                    size_t plen, const uint8_t *manifest_wire, size_t mlen,
                    const oc_fh_manifest_t *manifest)
{
	oc_fh_store_ram_t *r = (oc_fh_store_ram_t *)s->ctx;
	if (!r || !fr || !payload || !manifest_wire || !manifest) {
		return -1;
	}
	if (plen > sizeof(r->payload) || mlen > sizeof(r->wire)) {
		return -1;
	}
	r->fr = *fr;
	r->manifest = *manifest;
	memcpy(r->payload, payload, plen);
	r->plen = plen;
	memcpy(r->wire, manifest_wire, mlen);
	r->mlen = mlen;
	r->have_active = 1;
	if (fr->fence_seq > r->hwm) {
		r->hwm = fr->fence_seq;
	}
	return 0;
}

static int ram_load(oc_fh_store_t *s, oc_fh_freshness_t *fr, uint8_t *payload,
                    size_t payload_cap, size_t *out_plen, uint8_t *manifest_wire,
                    size_t wire_cap, size_t *out_mlen, oc_fh_manifest_t *manifest)
{
	oc_fh_store_ram_t *r = (oc_fh_store_ram_t *)s->ctx;
	if (!r || !fr || !payload || !out_plen || !manifest_wire || !out_mlen || !manifest) {
		return -1;
	}
	if (!r->have_active) {
		return -1;
	}
	if (r->plen > payload_cap || r->mlen > wire_cap) {
		return -1;
	}
	*fr = r->fr;
	*manifest = r->manifest;
	memcpy(payload, r->payload, r->plen);
	*out_plen = r->plen;
	memcpy(manifest_wire, r->wire, r->mlen);
	*out_mlen = r->mlen;
	return 0;
}

void oc_fh_store_ram_init(oc_fh_store_ram_t *ram)
{
	memset(ram, 0, sizeof(*ram));
	ram->api.ctx = ram;
	ram->api.get_hwm = ram_get_hwm;
	ram->api.set_hwm = ram_set_hwm;
	ram->api.save_active = ram_save;
	ram->api.load_active = ram_load;
}
