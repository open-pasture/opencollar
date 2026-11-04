#include "opencollar/fence_store.h"

#include <string.h>

/* Simple CRC-32 (IEEE); used only for A/B integrity in the RAM backend. */
static uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t len)
{
	size_t i;
	unsigned b;

	crc = ~crc;
	for (i = 0; i < len; i++) {
		crc ^= data[i];
		for (b = 0; b < 8; b++) {
			uint32_t mask = -(crc & 1u);
			crc = (crc >> 1) ^ (0xEDB88320u & mask);
		}
	}
	return ~crc;
}

static uint32_t slot_crc(const oc_fh_store_ram_slot_t *sl)
{
	uint32_t c = 0;
	c = crc32_update(c, (const uint8_t *)&sl->hwm, sizeof(sl->hwm));
	c = crc32_update(c, (const uint8_t *)&sl->fr, sizeof(sl->fr));
	c = crc32_update(c, (const uint8_t *)&sl->manifest, sizeof(sl->manifest));
	c = crc32_update(c, (const uint8_t *)&sl->plen, sizeof(sl->plen));
	c = crc32_update(c, (const uint8_t *)&sl->mlen, sizeof(sl->mlen));
	if (sl->plen) {
		c = crc32_update(c, sl->payload, sl->plen);
	}
	if (sl->mlen) {
		c = crc32_update(c, sl->wire, sl->mlen);
	}
	return c;
}

static int slot_ok(const oc_fh_store_ram_slot_t *sl)
{
	return sl->occupied && sl->crc == slot_crc(sl);
}

static const oc_fh_store_ram_slot_t *best_slot(const oc_fh_store_ram_t *r)
{
	uint8_t pri = (uint8_t)(r->primary & 1u);
	uint8_t alt = (uint8_t)(pri ^ 1u);
	int ok_pri = slot_ok(&r->slot[pri]);
	int ok_alt = slot_ok(&r->slot[alt]);

	/* Both valid → higher fence_seq wins (ignore stale primary pointer). */
	if (ok_pri && ok_alt) {
		if (r->slot[alt].fr.fence_seq > r->slot[pri].fr.fence_seq) {
			return &r->slot[alt];
		}
		return &r->slot[pri];
	}
	if (ok_pri) {
		return &r->slot[pri];
	}
	if (ok_alt) {
		return &r->slot[alt];
	}
	return NULL;
}

int oc_fh_store_ram_have_active(const oc_fh_store_ram_t *ram)
{
	return ram && best_slot(ram) != NULL;
}

uint32_t oc_fh_store_ram_hwm(const oc_fh_store_ram_t *ram)
{
	const oc_fh_store_ram_slot_t *sl;

	if (!ram) {
		return 0;
	}
	sl = best_slot(ram);
	return sl ? sl->hwm : 0;
}

static int ram_get_hwm(oc_fh_store_t *s, uint32_t *out_seq)
{
	oc_fh_store_ram_t *r = (oc_fh_store_ram_t *)s->ctx;
	if (!r || !out_seq) {
		return -1;
	}
	*out_seq = oc_fh_store_ram_hwm(r);
	return 0;
}

static int ram_set_hwm(oc_fh_store_t *s, uint32_t seq)
{
	/* Soft/optional: durable HWM advances only inside save_active. */
	(void)s;
	(void)seq;
	return 0;
}

static int ram_save(oc_fh_store_t *s, const oc_fh_freshness_t *fr, const uint8_t *payload,
                    size_t plen, const uint8_t *manifest_wire, size_t mlen,
                    const oc_fh_manifest_t *manifest)
{
	oc_fh_store_ram_t *r = (oc_fh_store_ram_t *)s->ctx;
	uint8_t idx;
	oc_fh_store_ram_slot_t *sl;
	uint32_t prev_hwm;

	if (!r || !fr || !payload || !manifest_wire || !manifest) {
		return -1;
	}
	if (plen > sizeof(r->slot[0].payload) || mlen > sizeof(r->slot[0].wire)) {
		return -1;
	}
	if (r->fail_next_save) {
		r->fail_next_save = 0;
		return -1;
	}

	prev_hwm = oc_fh_store_ram_hwm(r);

	/* Alternate into the non-primary slot (A/B). */
	idx = (uint8_t)((r->primary ^ 1u) & 1u);
	sl = &r->slot[idx];
	memset(sl, 0, sizeof(*sl));
	sl->hwm = fr->fence_seq > prev_hwm ? fr->fence_seq : prev_hwm;
	sl->fr = *fr;
	sl->manifest = *manifest;
	memcpy(sl->payload, payload, plen);
	sl->plen = plen;
	memcpy(sl->wire, manifest_wire, mlen);
	sl->mlen = mlen;
	sl->occupied = 1;
	sl->crc = slot_crc(sl);

	if (r->tear_next_save) {
		/*
		 * Torn write: primary advanced to the new slot but CRC is bad
		 * (power cut mid-commit). load/get_hwm fall back to the other
		 * copy → old fence and old HWM together.
		 */
		r->tear_next_save = 0;
		sl->crc ^= 0xFFFFFFFFu;
		r->primary = idx;
		return 0;
	}

	r->primary = idx;
	return 0;
}

static int load_from_slot(const oc_fh_store_ram_slot_t *sl, oc_fh_freshness_t *fr,
                          uint8_t *payload, size_t payload_cap, size_t *out_plen,
                          uint8_t *manifest_wire, size_t wire_cap, size_t *out_mlen,
                          oc_fh_manifest_t *manifest)
{
	if (!slot_ok(sl)) {
		return -1;
	}
	if (sl->plen > payload_cap || sl->mlen > wire_cap) {
		return -1;
	}
	*fr = sl->fr;
	*manifest = sl->manifest;
	memcpy(payload, sl->payload, sl->plen);
	*out_plen = sl->plen;
	memcpy(manifest_wire, sl->wire, sl->mlen);
	*out_mlen = sl->mlen;
	return 0;
}

static int ram_load(oc_fh_store_t *s, oc_fh_freshness_t *fr, uint8_t *payload,
                    size_t payload_cap, size_t *out_plen, uint8_t *manifest_wire,
                    size_t wire_cap, size_t *out_mlen, oc_fh_manifest_t *manifest)
{
	oc_fh_store_ram_t *r = (oc_fh_store_ram_t *)s->ctx;
	const oc_fh_store_ram_slot_t *sl;

	if (!r || !fr || !payload || !out_plen || !manifest_wire || !out_mlen || !manifest) {
		return -1;
	}
	sl = best_slot(r);
	if (!sl) {
		return -1;
	}
	return load_from_slot(sl, fr, payload, payload_cap, out_plen, manifest_wire, wire_cap,
	                      out_mlen, manifest);
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
