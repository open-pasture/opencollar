# Monocypher

Ed25519 signature checks for boundary and config commands. Monocypher 4.0.2
by Loup Vaillant and contributors, dual-licensed CC0-1.0 or BSD-2-Clause
(`LICENCE.md`).

Files taken unchanged from `monocypher-4.0.2.tar.gz` (https://monocypher.org/download/,
SHA-512 `bf275d4c53ff94af6cdc723a4e002e9f080f4d1436c86c76bb37870b34807f1d7b32331d8ff8a1aeb369e946f3769021e03e63efac25b82efc5abf54dc084714`,
matching the published checksum): `src/monocypher.c`, `src/monocypher.h`,
`src/optional/monocypher-ed25519.c`, `src/optional/monocypher-ed25519.h`.

The firmware uses `crypto_sha512_init/update/final`, `crypto_eddsa_reduce` and
`crypto_eddsa_check_equation`, so the canonical command streams into SHA-512
without a second 12 KB buffer.
