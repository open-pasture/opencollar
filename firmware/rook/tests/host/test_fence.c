/* SPDX-License-Identifier: Apache-2.0 */
/* Signed fences from the mock server: verified with command.c, stored as a
 * slot, handed to the LoRa sink once per rising fence_seq. */
#include <stdio.h>

#include "rook_fence.h"
#include "store_ram.h"
#include "test.h"

static struct app a;
static char reply[256];
static char wire[4096];
static uint32_t sunk_seq;
static int sunk;

static const struct cue_config cue_cfg = {0};
static const struct geofence_config gdef = {.warn_m = 5, .hysteresis_m = 1};

static size_t load(const char *name)
{
	char path[256];
	FILE *f;
	size_t n;

	snprintf(path, sizeof(path), SAMPLES "/%s", name);
	f = fopen(path, "rb");
	if (!f) {
		printf("missing %s\n", path);
		exit(1);
	}
	n = fread(wire, 1, sizeof(wire) - 1, f);
	fclose(f);
	while (n && (wire[n - 1] == '\n' || wire[n - 1] == '\r')) {
		n--;
	}
	wire[n] = 0;
	return n;
}

static void sink(void *ctx, uint32_t seq, const char *w, size_t len)
{
	(void)ctx;
	(void)w;
	CHECK(len > 0);
	sunk_seq = seq;
	sunk++;
}

int main(void)
{
	const char *prov = "provision {\"v\":1,\"c\":\"col_01J9SIMCOLLAR\",\"h\":\"herd_01J7GOLDEN\","
			   "\"k\":\"0123456789abcdef0123456789abcdef\","
			   "\"e\":\"https://farm.example.com/collar/v1\","
			   "\"s\":\"A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg=\"}";
	struct rook_fence_result r;
	size_t n;

	store_ram_reset();
	app_init(&a, &cue_cfg, &gdef);
	app_boot(&a, 0);
	app_line(&a, prov, strlen(prov), false, 0, reply, sizeof(reply));
	CHECK(strcmp(reply, "ok col_01J9SIMCOLLAR") == 0);
	rook_fence_reset();
	rook_fence_set_sink(sink, NULL);

	n = load("boundary_v1.json");
	r = rook_fence_download(&a, wire, n, 1000);
	CHECK(r.code == REJECT_NONE && r.has_ack && r.handed_on);
	CHECK(sunk == 1 && sunk_seq == 1 && rook_fence_seq() == 1);

	/* The same again: a duplicate (re-acked by slots), not handed on */
	r = rook_fence_download(&a, wire, n, 2000);
	CHECK(r.has_ack && !r.handed_on && sunk == 1);

	/* Tampered (version changed after signing): bad_sig, not handed on */
	n = load("boundary_tampered.json");
	r = rook_fence_download(&a, wire, n, 3000);
	CHECK(r.code == REJECT_BAD_SIG && !r.handed_on && sunk == 1);

	n = load("boundary_v2.json");
	r = rook_fence_download(&a, wire, n, 4000);
	CHECK(r.code == REJECT_NONE && r.handed_on && sunk == 2 && sunk_seq == 2);
	return test_done("rook fence");
}
