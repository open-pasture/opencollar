/*
 * Store: a power cut at every byte of every write leaves the old state or
 * the new one; bad CRCs and unknown formats are ignored; an empty store
 * means no cues.
 */
#include "../../src/app.h"
#include "../../src/config.h"
#include "../../src/slots.h"
#include "../../src/store.h"
#include "slot_fixtures.h"
#include "store_ram.h"

#define T0 1790510400

static int32_t scratch[SHAPE_BUF_VERTICES][2];
static int32_t cmd_buf[SHAPE_BUF_VERTICES][2];
static struct store_ram_image before;

static struct {
	uint32_t version;
	uint16_t total;
	int32_t first[2];
} fence;

static void on_apply(void *ctx, const struct slot_hdr *h, const int32_t (*v)[2])
{
	(void)ctx;
	fence.version = h->version;
	fence.total = h->total;
	fence.first[0] = v[0][0];
	fence.first[1] = v[0][1];
}

static void fresh(struct slots *s)
{
	slots_init(s, &LIMITS_V0, scratch, on_apply, NULL);
}

static void insert(struct slots *s, uint32_t version, bool staged, int64_t eff, int vertices,
		   int64_t now)
{
	static struct boundary_cmd cmd;

	fx_command(&cmd, cmd_buf, version, "herd_1", NULL, staged, eff, vertices, &LIMITS_V0);
	slots_insert(s, &cmd, true, now);
}

/* Versions held after a reboot, as "a1 2 3" (a = active) */
static void held(char *out, size_t cap)
{
	static struct slots s;
	size_t n = 0;

	fresh(&s);
	memset(&fence, 0, sizeof(fence));
	slots_load(&s);
	out[0] = '\0';
	for (int i = 0; i < s.n && n < cap; i++) {
		n += (size_t)snprintf(out + n, cap - n, "%s%s%u", i ? " " : "",
				      (s.s[i].flags & SLOT_F_APPLIED) ? "a" : "",
				      (unsigned)s.s[i].version);
	}
	/* The fence got the active record's own geometry */
	if (slots_active(&s)) {
		CHECK(fence.version == s.s[0].version && fence.total == s.s[0].total);
	}
}

typedef void (*op_fn)(struct slots *s);

/* Run op from the saved image with the power cut after every possible byte */
static void sweep(const char *what, op_fn op, const char *old_state, const char *new_state)
{
	static struct slots s;
	char got[128];
	size_t w0, total;
	int olds = 0, news = 0;

	/* How many bytes the operation writes */
	store_ram_load(&before);
	fresh(&s);
	slots_load(&s);
	w0 = store_ram_written();
	op(&s);
	total = store_ram_written() - w0;
	held(got, sizeof(got));
	CHECK_CASE(strcmp(got, new_state) == 0, what, "completed: '%s', want '%s'", got,
		   new_state);

	for (size_t cut = 0; cut <= total; cut++) {
		store_ram_load(&before);
		fresh(&s);
		slots_load(&s);
		store_ram_cut_after((long)cut);
		op(&s);
		store_ram_reboot();
		held(got, sizeof(got));
		if (strcmp(got, old_state) == 0) {
			olds++;
		} else if (strcmp(got, new_state) == 0) {
			news++;
		} else {
			CHECK_CASE(false, what, "cut after %zu of %zu bytes: '%s'", cut, total, got);
		}
	}
	CHECK_CASE(olds > 0 && news > 0, what, "old %d, new %d", olds, news);
	printf("%s: %zu bytes written, power cut at each: %d old, %d new\n", what, total, olds,
	       news);
}

static void op_immediate(struct slots *s)
{
	insert(s, 3, false, 0, 384, T0 + 10);
}

static void op_staged(struct slots *s)
{
	/* Activates before v2, so v2 is dead and goes */
	insert(s, 3, true, T0 + 60, 12, T0 + 10);
}

static void op_tick(struct slots *s)
{
	struct slot_ack ack;

	slots_tick(s, T0 + 120, &ack);
}

static void setup_v1_active_v2_staged(void)
{
	static struct slots s;

	store_ram_reset();
	fresh(&s);
	insert(&s, 1, false, 0, 4, T0);
	insert(&s, 2, true, T0 + 120, 8, T0);
	store_ram_save(&before);
}

static void test_power_cuts(void)
{
	setup_v1_active_v2_staged();
	sweep("immediate insert", op_immediate, "a1 2", "a3");
	sweep("staged insert", op_staged, "a1 2", "a1 3");
	sweep("tick applies staged", op_tick, "a1 2", "a2");
}

/* One record write on its own: old or new, never a mix */
static void test_single_write(void)
{
	static struct slots s;
	struct slot_ack ack;
	char got[64];
	size_t w0, total;

	store_ram_reset();
	fresh(&s);
	insert(&s, 1, true, T0 + 60, 4, T0);
	store_ram_save(&before);
	w0 = store_ram_written();
	slots_tick(&s, T0 + 60, &ack); /* Rewrites the record in place with applied set */
	total = store_ram_written() - w0;
	for (size_t cut = 0; cut <= total; cut++) {
		store_ram_load(&before);
		fresh(&s);
		slots_load(&s);
		store_ram_cut_after((long)cut);
		slots_tick(&s, T0 + 60, &ack);
		store_ram_reboot();
		held(got, sizeof(got));
		CHECK_CASE(strcmp(got, "1") == 0 || strcmp(got, "a1") == 0, "rewrite", "cut %zu: '%s'",
			   cut, got);
	}
}

static void test_bad_records_ignored(void)
{
	static struct slots s;
	static uint8_t rec[SLOT_RECORD_MAX];
	char got[64];
	int len;

	/* A flipped bit in the stored record: ignored, and its id is reused */
	store_ram_reset();
	fresh(&s);
	insert(&s, 1, false, 0, 4, T0);
	held(got, sizeof(got));
	CHECK(strcmp(got, "a1") == 0);
	CHECK(store_ram_corrupt(STORE_ID_SLOT_BASE, 100));
	held(got, sizeof(got));
	CHECK(strcmp(got, "") == 0);
	fresh(&s);
	slots_load(&s);
	insert(&s, 2, false, 0, 4, T0);
	held(got, sizeof(got));
	CHECK(strcmp(got, "a2") == 0);

	/* A format this firmware doesn't know: ignored */
	store_ram_reset();
	fresh(&s);
	insert(&s, 5, false, 0, 4, T0);
	len = store_read(STORE_ID_SLOT_BASE, rec, sizeof(rec));
	CHECK(len == 192 + 32);
	rec[4] = 9;
	CHECK(store_write(STORE_ID_SLOT_BASE, rec, (size_t)len) == 0);
	held(got, sizeof(got));
	CHECK(strcmp(got, "") == 0);

	/* A record of the wrong size, or not a record at all */
	CHECK(store_write(STORE_ID_SLOT_BASE + 1, "OCS1 hello", 10) == 0);
	held(got, sizeof(got));
	CHECK(strcmp(got, "") == 0);

	/* A good staged record next to a bad active one: the staged one waits */
	store_ram_reset();
	fresh(&s);
	insert(&s, 1, false, 0, 4, T0);
	insert(&s, 2, true, T0 + 60, 4, T0);
	CHECK(store_ram_corrupt(STORE_ID_SLOT_BASE, 20));
	held(got, sizeof(got));
	CHECK(strcmp(got, "2") == 0);
}

static void test_empty_store_no_cues(void)
{
	static struct app a;
	const struct cue_config cue = {2730, 1000, 300, 20000, 30000, 10000};
	const struct geofence_config gcfg = {5.0, 1.0, 10.0};
	int cues = 0;

	store_ram_reset();
	app_init(&a, &cue, &gcfg);
	app_boot(&a, 0);
	CHECK(!a.prov.ok && a.fence == NULL);

	/* Walk 200 m through where any fence could be: no fence, no cue */
	for (int i = 0; i < 200; i++) {
		struct app_fix_in f = {
			.valid = true,
			.lat = AMES_LAT + i * 0.00001,
			.lon = AMES_LON,
			.accuracy_m = 2,
			.has_time = true,
			.utc = T0 + i,
		};
		struct app_fix_out out = app_fix(&a, &f, i * 1000);

		CHECK(!out.fenced);
		cues += out.cmd.active;
	}
	CHECK(cues == 0);
}

int main(void)
{
	test_power_cuts();
	test_single_write();
	test_bad_records_ignored();
	test_empty_store_no_cues();
	return test_done("store");
}
