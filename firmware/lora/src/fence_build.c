#include "fence_build.h"

#include <string.h>

int oc_fh_build_signed(oc_fh_built_t *out, const uint8_t farm_id[8], uint32_t fence_seq,
                       uint32_t issued_at, const uint8_t *payload, size_t plen,
                       uint16_t frag_data_max, oc_fh_sign_fn sign, void *sign_ctx)
{
	uint16_t count;
	uint16_t i;
	size_t off;

	if (!out || !farm_id || !payload || !sign || plen == 0 || plen > OC_FH_MAX_PAYLOAD) {
		return -1;
	}
	if (frag_data_max == 0) {
		frag_data_max = (uint16_t)OC_FH_DEFAULT_FRAG_DATA;
	}
	count = (uint16_t)((plen + frag_data_max - 1) / frag_data_max);
	if (count == 0 || count > OC_FH_MAX_FRAGMENTS) {
		return -1;
	}
	memset(out, 0, sizeof(*out));
	memcpy(out->manifest.farm_id, farm_id, OC_FH_FARM_ID_LEN);
	out->manifest.fence_seq = fence_seq;
	out->manifest.issued_at = issued_at;
	out->manifest.frag_count = count;
	out->frag_data_max = frag_data_max;
	oc_fh_hash_payload(out->manifest.poly_hash, payload, plen);
	off = 0;
	for (i = 0; i < count; i++) {
		size_t rem = plen - off;
		uint16_t dlen = (uint16_t)(rem > frag_data_max ? frag_data_max : rem);
		oc_fh_hash_fragment(out->manifest.frag_hash[i], payload + off, dlen);
		off += dlen;
	}
	out->sealed_len =
	    oc_fh_manifest_seal(&out->manifest, out->sealed, sizeof(out->sealed), sign, sign_ctx);
	return out->sealed_len ? 0 : -1;
}
