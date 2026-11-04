#include "opencollar/fence_wire.h"

#include "fence_util.h"

#include <string.h>

void oc_fh_bitmap_set(uint8_t *bm, unsigned bit)
{
	bm[bit / 8u] |= (uint8_t)(1u << (bit % 8u));
}

void oc_fh_bitmap_clear(uint8_t *bm, unsigned bit)
{
	bm[bit / 8u] &= (uint8_t)~(1u << (bit % 8u));
}

int oc_fh_bitmap_get(const uint8_t *bm, unsigned bit)
{
	return (bm[bit / 8u] >> (bit % 8u)) & 1;
}

size_t oc_fh_encode_beacon(const oc_fh_beacon_t *b, uint8_t *out, size_t cap)
{
	size_t need = 1 + OC_FH_FARM_ID_LEN + 4 + OC_FH_SHORT_HASH_LEN + 1;

	if (!b || !out || cap < need) {
		return 0;
	}
	out[0] = (uint8_t)OC_FH_MSG_BEACON;
	memcpy(out + 1, b->farm_id, OC_FH_FARM_ID_LEN);
	oc_fh_be32(out + 1 + OC_FH_FARM_ID_LEN, b->fence_seq);
	memcpy(out + 1 + OC_FH_FARM_ID_LEN + 4, b->short_hash, OC_FH_SHORT_HASH_LEN);
	out[1 + OC_FH_FARM_ID_LEN + 4 + OC_FH_SHORT_HASH_LEN] = b->hop_reserved;
	return need;
}

int oc_fh_decode_beacon(oc_fh_beacon_t *b, const uint8_t *in, size_t len)
{
	size_t need = 1 + OC_FH_FARM_ID_LEN + 4 + OC_FH_SHORT_HASH_LEN + 1;

	if (!b || !in || len != need || in[0] != OC_FH_MSG_BEACON) {
		return -1;
	}
	memcpy(b->farm_id, in + 1, OC_FH_FARM_ID_LEN);
	b->fence_seq = oc_fh_rd32(in + 1 + OC_FH_FARM_ID_LEN);
	memcpy(b->short_hash, in + 1 + OC_FH_FARM_ID_LEN + 4, OC_FH_SHORT_HASH_LEN);
	b->hop_reserved = in[1 + OC_FH_FARM_ID_LEN + 4 + OC_FH_SHORT_HASH_LEN];
	return 0;
}

size_t oc_fh_encode_fragment(const oc_fh_fragment_t *f, uint8_t *out, size_t cap)
{
	size_t need;

	if (!f || !out || !f->data || f->data_len == 0 || f->count == 0 ||
	    f->count > OC_FH_MAX_FRAGMENTS || f->idx >= f->count) {
		return 0;
	}
	need = 1 + OC_FH_FARM_ID_LEN + 4 + 2 + 2 + f->data_len;
	if (need > cap) {
		return 0;
	}
	out[0] = (uint8_t)OC_FH_MSG_FRAGMENT;
	memcpy(out + 1, f->farm_id, OC_FH_FARM_ID_LEN);
	oc_fh_be32(out + 1 + OC_FH_FARM_ID_LEN, f->fence_seq);
	oc_fh_be16(out + 1 + OC_FH_FARM_ID_LEN + 4, f->idx);
	oc_fh_be16(out + 1 + OC_FH_FARM_ID_LEN + 6, f->count);
	memcpy(out + 1 + OC_FH_FARM_ID_LEN + 8, f->data, f->data_len);
	return need;
}

int oc_fh_decode_fragment(oc_fh_fragment_t *f, const uint8_t *in, size_t len)
{
	size_t hdr = 1 + OC_FH_FARM_ID_LEN + 4 + 2 + 2;

	if (!f || !in || len <= hdr || in[0] != OC_FH_MSG_FRAGMENT) {
		return -1;
	}
	memcpy(f->farm_id, in + 1, OC_FH_FARM_ID_LEN);
	f->fence_seq = oc_fh_rd32(in + 1 + OC_FH_FARM_ID_LEN);
	f->idx = oc_fh_rd16(in + 1 + OC_FH_FARM_ID_LEN + 4);
	f->count = oc_fh_rd16(in + 1 + OC_FH_FARM_ID_LEN + 6);
	f->data = in + hdr;
	f->data_len = (uint16_t)(len - hdr);
	if (f->count == 0 || f->count > OC_FH_MAX_FRAGMENTS || f->idx >= f->count ||
	    f->data_len == 0) {
		return -1;
	}
	return 0;
}

size_t oc_fh_encode_need(const oc_fh_need_t *n, uint8_t *out, size_t cap)
{
	size_t need;

	if (!n || !out || n->bitmap_len == 0 ||
	    n->bitmap_len > (OC_FH_MAX_FRAGMENTS / 8u)) {
		return 0;
	}
	need = 1 + OC_FH_FARM_ID_LEN + 4 + 2 + 1 + n->bitmap_len;
	if (need > cap) {
		return 0;
	}
	out[0] = (uint8_t)OC_FH_MSG_NEED;
	memcpy(out + 1, n->farm_id, OC_FH_FARM_ID_LEN);
	oc_fh_be32(out + 1 + OC_FH_FARM_ID_LEN, n->fence_seq);
	oc_fh_be16(out + 1 + OC_FH_FARM_ID_LEN + 4, n->from);
	out[1 + OC_FH_FARM_ID_LEN + 6] = n->bitmap_len;
	memcpy(out + 1 + OC_FH_FARM_ID_LEN + 7, n->bitmap, n->bitmap_len);
	return need;
}

int oc_fh_decode_need(oc_fh_need_t *n, const uint8_t *in, size_t len)
{
	size_t hdr = 1 + OC_FH_FARM_ID_LEN + 4 + 2 + 1;
	uint8_t blen;

	if (!n || !in || len < hdr || in[0] != OC_FH_MSG_NEED) {
		return -1;
	}
	blen = in[1 + OC_FH_FARM_ID_LEN + 6];
	if (blen == 0 || blen > (OC_FH_MAX_FRAGMENTS / 8u) || len != hdr + blen) {
		return -1;
	}
	memcpy(n->farm_id, in + 1, OC_FH_FARM_ID_LEN);
	n->fence_seq = oc_fh_rd32(in + 1 + OC_FH_FARM_ID_LEN);
	n->from = oc_fh_rd16(in + 1 + OC_FH_FARM_ID_LEN + 4);
	n->bitmap_len = blen;
	memcpy(n->bitmap, in + hdr, blen);
	return 0;
}

size_t oc_fh_encode_have(const oc_fh_have_t *h, uint8_t *out, size_t cap)
{
	size_t need = 1 + OC_FH_FARM_ID_LEN + 4 + OC_FH_SHORT_HASH_LEN;

	if (!h || !out || cap < need) {
		return 0;
	}
	out[0] = (uint8_t)OC_FH_MSG_HAVE;
	memcpy(out + 1, h->farm_id, OC_FH_FARM_ID_LEN);
	oc_fh_be32(out + 1 + OC_FH_FARM_ID_LEN, h->fence_seq);
	memcpy(out + 1 + OC_FH_FARM_ID_LEN + 4, h->short_hash, OC_FH_SHORT_HASH_LEN);
	return need;
}

int oc_fh_decode_have(oc_fh_have_t *h, const uint8_t *in, size_t len)
{
	size_t need = 1 + OC_FH_FARM_ID_LEN + 4 + OC_FH_SHORT_HASH_LEN;

	if (!h || !in || len != need || in[0] != OC_FH_MSG_HAVE) {
		return -1;
	}
	memcpy(h->farm_id, in + 1, OC_FH_FARM_ID_LEN);
	h->fence_seq = oc_fh_rd32(in + 1 + OC_FH_FARM_ID_LEN);
	memcpy(h->short_hash, in + 1 + OC_FH_FARM_ID_LEN + 4, OC_FH_SHORT_HASH_LEN);
	return 0;
}
