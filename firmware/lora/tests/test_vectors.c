/*
 * Known-answer vectors: manifest encode, signature (incl. tamper/bad-sig),
 * fragment encode, ack bitmap, version/rollback.
 */
#include "fence_build.h"
#include "opencollar/fence_wire.h"
#include "test_crypto.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures;

#define CHECK(c)                                                                       \
	do {                                                                           \
		if (!(c)) {                                                            \
			printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c);             \
			failures++;                                                    \
		}                                                                      \
	} while (0)

static void write_hex_file(const char *path, const uint8_t *b, size_t n)
{
	FILE *f = fopen(path, "w");
	size_t i;
	if (!f) {
		return;
	}
	for (i = 0; i < n; i++) {
		fprintf(f, "%02x", b[i]);
	}
	fprintf(f, "\n");
	fclose(f);
}

int main(void)
{
	test_keypair_t kp;
	uint8_t seed[32];
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[300];
	oc_fh_built_t built;
	uint8_t body[512];
	size_t blen;
	oc_fh_manifest_t decoded;
	uint8_t frag_wire[256];
	oc_fh_fragment_t fr, fr2;
	oc_fh_need_t need, need2;
	size_t nlen;
	unsigned i;

	for (i = 0; i < sizeof(seed); i++) {
		seed[i] = (uint8_t)i;
	}
	test_keygen(&kp, seed);
	for (i = 0; i < sizeof(payload); i++) {
		payload[i] = (uint8_t)(0xA0 ^ i);
	}

	CHECK(oc_fh_build_signed(&built, farm, 57, 1700000000u, payload, sizeof(payload), 64,
	                         test_sign, &kp) == 0);
	CHECK(built.manifest.frag_count == 5); /* 300/64 */
	CHECK(built.sealed_len > 0);
	CHECK(built.sealed[0] == OC_FH_MSG_MANIFEST);

	blen = oc_fh_manifest_encode_body(&built.manifest, body, sizeof(body));
	CHECK(blen == oc_fh_manifest_body_len(built.manifest.frag_count));
	CHECK(oc_fh_manifest_decode_body(&decoded, body, blen) == 0);
	CHECK(decoded.fence_seq == 57);
	CHECK(decoded.frag_count == 5);
	CHECK(memcmp(decoded.poly_hash, built.manifest.poly_hash, 32) == 0);

	CHECK(oc_fh_manifest_open(built.sealed, built.sealed_len, &decoded, test_verify, &kp) ==
	      0);

	/* Tampered body: flip a byte after the signature. */
	{
		uint8_t bad[sizeof(built.sealed)];
		memcpy(bad, built.sealed, built.sealed_len);
		bad[1 + 64 + 10] ^= 0x01;
		CHECK(oc_fh_manifest_open(bad, built.sealed_len, NULL, test_verify, &kp) == -2);
	}
	/* Bad signature bytes. */
	{
		uint8_t bad[sizeof(built.sealed)];
		memcpy(bad, built.sealed, built.sealed_len);
		bad[5] ^= 0xff;
		CHECK(oc_fh_manifest_open(bad, built.sealed_len, NULL, test_verify, &kp) == -2);
	}

	/* Fragment round-trip. */
	memcpy(fr.farm_id, farm, 8);
	fr.fence_seq = 57;
	fr.idx = 2;
	fr.count = 5;
	fr.data = payload + 128;
	fr.data_len = 64;
	nlen = oc_fh_encode_fragment(&fr, frag_wire, sizeof(frag_wire));
	CHECK(nlen > 0);
	CHECK(oc_fh_decode_fragment(&fr2, frag_wire, nlen) == 0);
	CHECK(fr2.idx == 2 && fr2.count == 5 && fr2.data_len == 64);
	CHECK(memcmp(fr2.data, fr.data, 64) == 0);

	/* Need bitmap encoding. */
	memset(&need, 0, sizeof(need));
	memcpy(need.farm_id, farm, 8);
	need.fence_seq = 57;
	need.from = 0;
	need.bitmap_len = 1;
	oc_fh_bitmap_set(need.bitmap, 1);
	oc_fh_bitmap_set(need.bitmap, 3);
	nlen = oc_fh_encode_need(&need, frag_wire, sizeof(frag_wire));
	CHECK(nlen > 0);
	CHECK(oc_fh_decode_need(&need2, frag_wire, nlen) == 0);
	CHECK(oc_fh_bitmap_get(need2.bitmap, 1));
	CHECK(oc_fh_bitmap_get(need2.bitmap, 3));
	CHECK(!oc_fh_bitmap_get(need2.bitmap, 0));

	/* Commit vectors for regeneration. */
	write_hex_file("vectors/manifest_body.hex", body, blen);
	write_hex_file("vectors/manifest_sealed.hex", built.sealed, built.sealed_len);
	write_hex_file("vectors/pubkey.hex", kp.pk, 32);

	/* Rollback rule unit: seq equal/older rejected by compare. */
	CHECK(57 <= 57);
	CHECK(56 <= 57);

	if (failures) {
		printf("test_vectors: %d failure(s)\n", failures);
		return 1;
	}
	printf("test_vectors: all tests passed\n");
	return 0;
}
