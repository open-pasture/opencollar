/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#include "oc_fh_store_nvs.h"

#include <string.h>

#include "protocol.h"
#include "store.h"

static uint32_t slot_crc(const starling_fh_nvs_slot_t *sl)
{
	uint32_t c = 0;

	c = proto_crc32(c, &sl->hwm, sizeof(sl->hwm));
	c = proto_crc32(c, &sl->fr, sizeof(sl->fr));
	c = proto_crc32(c, &sl->manifest, sizeof(sl->manifest));
	c = proto_crc32(c, &sl->plen, sizeof(sl->plen));
	c = proto_crc32(c, &sl->mlen, sizeof(sl->mlen));
	if (sl->plen) {
		c = proto_crc32(c, sl->payload, sl->plen);
	}
	if (sl->mlen) {
		c = proto_crc32(c, sl->wire, sl->mlen);
	}
	return c;
}

static int slot_ok(const starling_fh_nvs_slot_t *sl)
{
	return sl->occupied && sl->crc == slot_crc(sl);
}

static int read_slot(uint16_t id, starling_fh_nvs_slot_t *sl)
{
	int n = store_read(id, sl, sizeof(*sl));

	if (n != (int)sizeof(*sl)) {
		memset(sl, 0, sizeof(*sl));
		return -1;
	}
	return slot_ok(sl) ? 0 : -1;
}

static const starling_fh_nvs_slot_t *best_of(const starling_fh_nvs_slot_t *a, int ok_a,
					    const starling_fh_nvs_slot_t *b, int ok_b)
{
	if (ok_a && ok_b) {
		return (b->fr.fence_seq > a->fr.fence_seq) ? b : a;
	}
	if (ok_a) {
		return a;
	}
	if (ok_b) {
		return b;
	}
	return NULL;
}

static int nvs_get_hwm(oc_fh_store_t *s, uint32_t *out_seq)
{
	starling_fh_nvs_slot_t s0, s1;
	const starling_fh_nvs_slot_t *best;
	int ok0, ok1;

	(void)s;
	if (!out_seq) {
		return -1;
	}
	ok0 = read_slot(STORE_ID_STARLING_FH_SLOT0, &s0) == 0;
	ok1 = read_slot(STORE_ID_STARLING_FH_SLOT1, &s1) == 0;
	best = best_of(&s0, ok0, &s1, ok1);
	*out_seq = best ? best->hwm : 0;
	return 0;
}

static int nvs_set_hwm(oc_fh_store_t *s, uint32_t seq)
{
	(void)s;
	(void)seq;
	return 0; /* soft; durable via save_active */
}

static int nvs_save(oc_fh_store_t *s, const oc_fh_freshness_t *fr, const uint8_t *payload,
		    size_t plen, const uint8_t *manifest_wire, size_t mlen,
		    const oc_fh_manifest_t *manifest)
{
	starling_fh_nvs_t *st = s->ctx;
	starling_fh_nvs_slot_t sl, cur0, cur1;
	uint32_t prev_hwm = 0;
	uint8_t idx;
	const starling_fh_nvs_slot_t *best;
	int ok0, ok1;

	if (!st || !fr || !payload || !manifest_wire || !manifest) {
		return -1;
	}
	if (plen > STARLING_FH_NVS_PAYLOAD_MAX || mlen > STARLING_FH_NVS_WIRE_MAX) {
		return -1;
	}

	ok0 = read_slot(STORE_ID_STARLING_FH_SLOT0, &cur0) == 0;
	ok1 = read_slot(STORE_ID_STARLING_FH_SLOT1, &cur1) == 0;
	best = best_of(&cur0, ok0, &cur1, ok1);
	if (best) {
		prev_hwm = best->hwm;
	}

	idx = (uint8_t)((st->primary ^ 1u) & 1u);
	memset(&sl, 0, sizeof(sl));
	sl.hwm = fr->fence_seq > prev_hwm ? fr->fence_seq : prev_hwm;
	sl.fr = *fr;
	sl.manifest = *manifest;
	sl.plen = (uint16_t)plen;
	sl.mlen = (uint16_t)mlen;
	memcpy(sl.payload, payload, plen);
	memcpy(sl.wire, manifest_wire, mlen);
	sl.occupied = 1;
	sl.crc = slot_crc(&sl);

	if (store_write(idx == 0 ? STORE_ID_STARLING_FH_SLOT0 : STORE_ID_STARLING_FH_SLOT1, &sl,
			sizeof(sl)) != 0) {
		return -1;
	}
	st->primary = idx;
	if (store_write(STORE_ID_STARLING_FH_PRIMARY, &st->primary, sizeof(st->primary)) != 0) {
		return -1;
	}
	return 0;
}

static int nvs_load(oc_fh_store_t *s, oc_fh_freshness_t *fr, uint8_t *payload, size_t payload_cap,
		    size_t *out_plen, uint8_t *manifest_wire, size_t wire_cap, size_t *out_mlen,
		    oc_fh_manifest_t *manifest)
{
	starling_fh_nvs_slot_t s0, s1;
	const starling_fh_nvs_slot_t *best;
	int ok0, ok1;

	(void)s;
	if (!fr || !payload || !out_plen || !manifest_wire || !out_mlen || !manifest) {
		return -1;
	}
	ok0 = read_slot(STORE_ID_STARLING_FH_SLOT0, &s0) == 0;
	ok1 = read_slot(STORE_ID_STARLING_FH_SLOT1, &s1) == 0;
	best = best_of(&s0, ok0, &s1, ok1);
	if (!best) {
		return -1;
	}
	if (best->plen > payload_cap || best->mlen > wire_cap) {
		return -1;
	}
	*fr = best->fr;
	*manifest = best->manifest;
	memcpy(payload, best->payload, best->plen);
	*out_plen = best->plen;
	memcpy(manifest_wire, best->wire, best->mlen);
	*out_mlen = best->mlen;
	return 0;
}

void starling_fh_nvs_init(starling_fh_nvs_t *s)
{
	uint8_t pri = 0;
	int n;

	memset(s, 0, sizeof(*s));
	n = store_read(STORE_ID_STARLING_FH_PRIMARY, &pri, sizeof(pri));
	if (n == (int)sizeof(pri) && (pri == 0 || pri == 1)) {
		s->primary = pri;
	}
	s->api.ctx = s;
	s->api.get_hwm = nvs_get_hwm;
	s->api.set_hwm = nvs_set_hwm;
	s->api.save_active = nvs_save;
	s->api.load_active = nvs_load;
	s->ready = 1;
}
