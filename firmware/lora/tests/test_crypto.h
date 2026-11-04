#ifndef OPENCOLLAR_TEST_CRYPTO_H
#define OPENCOLLAR_TEST_CRYPTO_H

#include "opencollar/fence_manifest.h"

#include "monocypher-ed25519.h"

#include <stdint.h>
#include <string.h>

typedef struct {
	uint8_t sk[64];
	uint8_t pk[32];
} test_keypair_t;

static inline void test_keygen(test_keypair_t *kp, const uint8_t seed[32])
{
	uint8_t s[32];
	memcpy(s, seed, 32);
	crypto_ed25519_key_pair(kp->sk, kp->pk, s);
}

static inline void test_sign(uint8_t sig[64], const uint8_t *msg, size_t len, void *ctx)
{
	const test_keypair_t *kp = ctx;
	crypto_ed25519_sign(sig, kp->sk, msg, len);
}

static inline int test_verify(const uint8_t sig[64], const uint8_t *msg, size_t len, void *ctx)
{
	const test_keypair_t *kp = ctx;
	return crypto_ed25519_check(sig, kp->pk, msg, len);
}

static inline int test_verify_pk(const uint8_t sig[64], const uint8_t *msg, size_t len, void *ctx)
{
	const uint8_t *pk = ctx;
	return crypto_ed25519_check(sig, pk, msg, len);
}

#endif
