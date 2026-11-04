#include "opencollar/fence_manifest.h"

#include "monocypher.h"

void oc_fh_hash_payload(uint8_t out[OC_FH_POLY_HASH_LEN], const uint8_t *data, size_t len)
{
	crypto_blake2b(out, OC_FH_POLY_HASH_LEN, data, len);
}

void oc_fh_hash_fragment(uint8_t out[OC_FH_FRAG_HASH_LEN], const uint8_t *data, size_t len)
{
	crypto_blake2b(out, OC_FH_FRAG_HASH_LEN, data, len);
}
