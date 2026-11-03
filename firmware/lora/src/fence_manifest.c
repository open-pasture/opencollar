#include "opencollar/fence_manifest.h"

#include "fence_util.h"

#include <string.h>

size_t oc_fh_manifest_body_len(uint16_t frag_count)
{
	if (frag_count == 0 || frag_count > OC_FH_MAX_FRAGMENTS) {
		return 0;
	}
	/* ver(1) + farm(8) + seq(4) + issued(4) + poly(32) + count(2) + hashes */
	return (size_t)1 + OC_FH_FARM_ID_LEN + 4 + 4 + OC_FH_POLY_HASH_LEN + 2 +
	       (size_t)frag_count * OC_FH_FRAG_HASH_LEN;
}

size_t oc_fh_manifest_encode_body(const oc_fh_manifest_t *m, uint8_t *out, size_t cap)
{
	size_t need;
	size_t off;
	uint16_t i;

	if (!m || !out) {
		return 0;
	}
	need = oc_fh_manifest_body_len(m->frag_count);
	if (need == 0 || need > cap) {
		return 0;
	}
	off = 0;
	out[off++] = (uint8_t)OC_FH_MANIFEST_VER;
	memcpy(out + off, m->farm_id, OC_FH_FARM_ID_LEN);
	off += OC_FH_FARM_ID_LEN;
	oc_fh_be32(out + off, m->fence_seq);
	off += 4;
	oc_fh_be32(out + off, m->issued_at);
	off += 4;
	memcpy(out + off, m->poly_hash, OC_FH_POLY_HASH_LEN);
	off += OC_FH_POLY_HASH_LEN;
	oc_fh_be16(out + off, m->frag_count);
	off += 2;
	for (i = 0; i < m->frag_count; i++) {
		memcpy(out + off, m->frag_hash[i], OC_FH_FRAG_HASH_LEN);
		off += OC_FH_FRAG_HASH_LEN;
	}
	return off;
}

int oc_fh_manifest_decode_body(oc_fh_manifest_t *m, const uint8_t *in, size_t len)
{
	size_t off;
	uint16_t i;
	uint16_t count;
	size_t need;

	if (!m || !in || len < 1 + OC_FH_FARM_ID_LEN + 4 + 4 + OC_FH_POLY_HASH_LEN + 2) {
		return -1;
	}
	off = 0;
	if (in[off++] != OC_FH_MANIFEST_VER) {
		return -1;
	}
	memcpy(m->farm_id, in + off, OC_FH_FARM_ID_LEN);
	off += OC_FH_FARM_ID_LEN;
	m->fence_seq = oc_fh_rd32(in + off);
	off += 4;
	m->issued_at = oc_fh_rd32(in + off);
	off += 4;
	memcpy(m->poly_hash, in + off, OC_FH_POLY_HASH_LEN);
	off += OC_FH_POLY_HASH_LEN;
	count = oc_fh_rd16(in + off);
	off += 2;
	need = oc_fh_manifest_body_len(count);
	if (need == 0 || len != need) {
		return -1;
	}
	m->frag_count = count;
	for (i = 0; i < count; i++) {
		memcpy(m->frag_hash[i], in + off, OC_FH_FRAG_HASH_LEN);
		off += OC_FH_FRAG_HASH_LEN;
	}
	return 0;
}

size_t oc_fh_manifest_seal(const oc_fh_manifest_t *m, uint8_t *out, size_t cap,
                           oc_fh_sign_fn sign, void *sign_ctx)
{
	size_t body_len;
	size_t pre_len;
	uint8_t pre[OC_FH_MANIFEST_DOMAIN_LEN + 1u + OC_FH_FARM_ID_LEN + 4u + 4u +
	            OC_FH_POLY_HASH_LEN + 2u + OC_FH_MAX_FRAGMENTS * OC_FH_FRAG_HASH_LEN];
	uint8_t body[sizeof(pre) - OC_FH_MANIFEST_DOMAIN_LEN];
	uint8_t sig[OC_FH_SIG_LEN];

	if (!m || !out || !sign) {
		return 0;
	}
	body_len = oc_fh_manifest_encode_body(m, body, sizeof(body));
	if (body_len == 0) {
		return 0;
	}
	if (1 + OC_FH_SIG_LEN + body_len > cap) {
		return 0;
	}
	memcpy(pre, OC_FH_MANIFEST_DOMAIN, OC_FH_MANIFEST_DOMAIN_LEN);
	memcpy(pre + OC_FH_MANIFEST_DOMAIN_LEN, body, body_len);
	pre_len = OC_FH_MANIFEST_DOMAIN_LEN + body_len;
	sign(sig, pre, pre_len, sign_ctx);
	out[0] = (uint8_t)OC_FH_MSG_MANIFEST;
	memcpy(out + 1, sig, OC_FH_SIG_LEN);
	memcpy(out + 1 + OC_FH_SIG_LEN, body, body_len);
	return 1 + OC_FH_SIG_LEN + body_len;
}

size_t oc_fh_manifest_encode_local(const oc_fh_manifest_t *m, uint8_t *out, size_t cap)
{
	size_t body_len;
	uint8_t body[OC_FH_MANIFEST_BODY_MAX];

	if (!m || !out) {
		return 0;
	}
	body_len = oc_fh_manifest_encode_body(m, body, sizeof(body));
	if (body_len == 0 || 1 + body_len > cap) {
		return 0;
	}
	out[0] = (uint8_t)OC_FH_MSG_MANIFEST_LOCAL;
	memcpy(out + 1, body, body_len);
	return 1 + body_len;
}

int oc_fh_manifest_open_local(const uint8_t *msg, size_t len, oc_fh_manifest_t *out_m)
{
	if (!msg || len < 2 || msg[0] != OC_FH_MSG_MANIFEST_LOCAL) {
		return -1;
	}
	return oc_fh_manifest_decode_body(out_m, msg + 1, len - 1);
}

int oc_fh_manifest_open(const uint8_t *msg, size_t len, oc_fh_manifest_t *out_m,
                        oc_fh_verify_fn verify, void *verify_ctx)
{
	const uint8_t *sig;
	const uint8_t *body;
	size_t body_len;
	uint8_t pre[OC_FH_MANIFEST_DOMAIN_LEN + 1u + OC_FH_FARM_ID_LEN + 4u + 4u +
	            OC_FH_POLY_HASH_LEN + 2u + OC_FH_MAX_FRAGMENTS * OC_FH_FRAG_HASH_LEN];
	size_t pre_len;
	oc_fh_manifest_t tmp;

	if (!msg || !verify || len < 1 + OC_FH_SIG_LEN + 1 + OC_FH_FARM_ID_LEN) {
		return -1;
	}
	if (msg[0] != OC_FH_MSG_MANIFEST) {
		return -1;
	}
	sig = msg + 1;
	body = msg + 1 + OC_FH_SIG_LEN;
	body_len = len - (1 + OC_FH_SIG_LEN);
	if (oc_fh_manifest_decode_body(&tmp, body, body_len) != 0) {
		return -1;
	}
	memcpy(pre, OC_FH_MANIFEST_DOMAIN, OC_FH_MANIFEST_DOMAIN_LEN);
	memcpy(pre + OC_FH_MANIFEST_DOMAIN_LEN, body, body_len);
	pre_len = OC_FH_MANIFEST_DOMAIN_LEN + body_len;
	if (verify(sig, pre, pre_len, verify_ctx) != 0) {
		return -2; /* bad sig */
	}
	if (out_m) {
		*out_m = tmp;
	}
	return 0;
}
