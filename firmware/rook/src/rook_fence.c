/* SPDX-License-Identifier: Apache-2.0 */
#include "rook_fence.h"

#include <errno.h>
#include <string.h>

#include "store.h"

#define HDR_MAGIC 0x31464b52u /* "RKF1" */

struct fence_hdr {
	uint32_t magic;
	uint32_t fence_seq;
	uint32_t len;
	uint32_t crc;         /* CRC-32 of the signed bytes */
	uint8_t bank;         /* 0 or 1 */
	uint8_t herd_len;
	uint8_t pad[2];
	uint8_t server_key[32];
	char herd[PROTO_MAX_ID_BYTES];
};

static rook_fence_sink_fn sink;
static void *sink_ctx;
static struct fence_hdr hdr; /* hdr.fence_seq: the high-water mark */
static bool hdr_ok;
static uint32_t hwm; /* The high-water mark (== hdr.fence_seq unless a write failed) */

void rook_fence_set_sink(rook_fence_sink_fn fn, void *ctx)
{
	sink = fn;
	sink_ctx = ctx;
}

uint32_t rook_fence_seq(void)
{
	return hwm;
}

void rook_fence_reset(void)
{
	sink = NULL;
	sink_ctx = NULL;
	memset(&hdr, 0, sizeof(hdr));
	hdr_ok = false;
	hwm = 0;
}

static uint16_t chunk_id(uint8_t bank, uint16_t i)
{
	return (uint16_t)(STORE_ID_ROOK_FENCE_BASE + bank * 16 + i);
}

static bool bound_to(const struct fence_hdr *h, const struct app *a)
{
	const struct proto_id *herd = app_herd(a);

	return herd && a->prov.ok && h->herd_len == herd->len &&
	       memcmp(h->herd, herd->s, herd->len) == 0 &&
	       memcmp(h->server_key, a->prov.server_key, 32) == 0;
}

uint32_t rook_fence_init(const struct app *a)
{
	struct fence_hdr h;

	hdr_ok = false;
	hwm = 0;
	memset(&hdr, 0, sizeof(hdr));
	if (store_read(STORE_ID_ROOK_FENCE, &h, sizeof(h)) != (int)sizeof(h) ||
	    h.magic != HDR_MAGIC || h.bank > 1 || h.len > ROOK_FENCE_MAX_BYTES ||
	    !bound_to(&h, a)) {
		return 0;
	}
	hdr = h;
	hdr_ok = true;
	hwm = h.fence_seq;
	return hwm;
}

int rook_fence_active(char *buf, size_t cap, uint32_t *fence_seq)
{
	size_t off = 0;

	if (!hdr_ok || hdr.len == 0) {
		return -ENOENT;
	}
	if (cap < hdr.len) {
		return -ENOMEM;
	}
	for (uint16_t i = 0; off < hdr.len; i++) {
		size_t n = hdr.len - off > ROOK_FENCE_CHUNK ? ROOK_FENCE_CHUNK : hdr.len - off;

		if (store_read(chunk_id(hdr.bank, i), buf + off, n) != (int)n) {
			return -EIO;
		}
		off += n;
	}
	if (proto_crc32(0, buf, hdr.len) != hdr.crc) {
		return -EIO;
	}
	if (fence_seq) {
		*fence_seq = hdr.fence_seq;
	}
	return (int)hdr.len;
}

static int persist(const struct app *a, uint32_t seq, const char *wire, size_t len)
{
	struct fence_hdr h = {0};
	const struct proto_id *herd = app_herd(a);
	size_t off = 0;

	if (len > ROOK_FENCE_MAX_BYTES || !herd) {
		return -EINVAL;
	}
	h.magic = HDR_MAGIC;
	h.fence_seq = seq;
	h.len = (uint32_t)len;
	h.crc = proto_crc32(0, wire, len);
	h.bank = hdr_ok ? (uint8_t)(hdr.bank ^ 1) : 0;
	h.herd_len = herd->len;
	memcpy(h.herd, herd->s, herd->len);
	memcpy(h.server_key, a->prov.server_key, 32);
	for (uint16_t i = 0; off < len; i++) {
		size_t n = len - off > ROOK_FENCE_CHUNK ? ROOK_FENCE_CHUNK : len - off;

		if (store_write(chunk_id(h.bank, i), wire + off, n) != 0) {
			return -EIO;
		}
		off += n;
	}
	if (store_write(STORE_ID_ROOK_FENCE, &h, sizeof(h)) != 0) {
		return -EIO;
	}
	hdr = h;
	hdr_ok = true;
	return 0;
}

/* The command's version, read without trusting it (only used to refuse) */
static bool peek_version(const char *wire, size_t len, uint32_t *v)
{
	struct wire_scan sc;
	const struct wire_span *sp;

	if (wire_scan(wire, len, &sc) != REJECT_NONE) {
		return false;
	}
	sp = wire_find(wire, &sc, "version");
	return sp && wire_u32(wire + sp->val, sp->val_len, v);
}

struct rook_fence_result rook_fence_download(struct app *a, const char *wire, size_t len,
					     int64_t now_ms)
{
	struct rook_fence_result r = {0};
	uint32_t v;

	/* At or below the persisted high-water mark: refused before it can
	 * touch the slots, even though it may be validly signed */
	if (rook_fence_seq() && peek_version(wire, len, &v) && v <= rook_fence_seq()) {
		r.code = REJECT_STALE;
		return r;
	}
	r.code = app_boundary(a, wire, len, now_ms, &r.ack, &r.has_ack);
	if (r.code != REJECT_NONE || !r.has_ack || r.ack.status == ACK_REJECTED) {
		return r;
	}
	if (r.ack.version > rook_fence_seq()) {
		/* On a failed write the fence is still enforced through the slots,
		 * which keep their own version; only re-gossip after reboot is lost */
		(void)persist(a, r.ack.version, wire, len);
		hwm = r.ack.version;
		if (sink) {
			sink(sink_ctx, r.ack.version, wire, len);
			r.handed_on = true;
		}
	}
	return r;
}
