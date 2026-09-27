/* Slots: slots.json through the real persistence path (boot reloads from the store) */
#include "../../src/slots.h"
#include "../../src/store.h"
#include "json.h"
#include "slot_fixtures.h"
#include "store_ram.h"

static int32_t scratch[SHAPE_BUF_VERTICES][2];
static int32_t cmd_buf[SHAPE_BUF_VERTICES][2];

/* What the apply callback saw last */
static struct {
	int calls;
	uint32_t version;
	uint16_t total;
	int32_t first[2];
} applied;

static void on_apply(void *ctx, const struct slot_hdr *h, const int32_t (*v)[2])
{
	(void)ctx;
	applied.calls++;
	applied.version = h->version;
	applied.total = h->total;
	applied.first[0] = v[0][0];
	applied.first[1] = v[0][1];
}

static struct collar_limits limits_of(const struct jval *l)
{
	struct collar_limits x = {
		.outer = (uint16_t)jnum(l, "outer"),
		.holes = (uint16_t)jnum(l, "holes"),
		.hole_vertices = (uint16_t)jnum(l, "hole_vertices"),
		.total = (uint16_t)jnum(l, "total"),
		.slots = (uint16_t)jnum(l, "slots"),
		.slot_bytes = (uint32_t)jnum(l, "slot_bytes"),
	};

	return x;
}

static bool time_of(const struct jval *obj, const char *key, int64_t *t)
{
	const char *s = jstr(obj, key);

	return s && proto_time_parse(s, strlen(s), t);
}

static void id_of(struct proto_id *id, const char *s)
{
	CHECK(proto_id_set(id, s, strlen(s)));
}

static void check_ack(const char *name, size_t step, const struct slot_ack *got,
		      const struct jval *want)
{
	char at[24] = "";
	const char *want_at = jstr(want, "at");
	const char *want_code = jstr(want, "code");

	if (got->has_at) {
		proto_time_format(got->at, at, sizeof(at));
	}
	CHECK_CASE(got->version == (uint32_t)jnum(want, "version"), name, "step %zu version %u",
		   step, (unsigned)got->version);
	CHECK_CASE(strcmp(ack_status_str(got->status), jstr(want, "status")) == 0, name,
		   "step %zu status %s", step, ack_status_str(got->status));
	CHECK_CASE(strcmp(reject_str(got->code), want_code ? want_code : "") == 0, name,
		   "step %zu code '%s'", step, reject_str(got->code));
	CHECK_CASE(strcmp(at, want_at ? want_at : "") == 0, name, "step %zu at '%s', want '%s'",
		   step, at, want_at ? want_at : "");
}

static void run_case(const struct jval *k)
{
	static struct slots s;
	static struct boundary_cmd cmd;
	const char *name = jstr(k, "name");
	const struct jval *steps = jget(k, "steps");
	const struct jval *expect = jget(k, "expect");
	struct collar_limits lim = limits_of(jget(k, "limits"));
	struct proto_id herd, collar;

	store_ram_reset();
	memset(&applied, 0, sizeof(applied));
	slots_init(&s, &lim, scratch, on_apply, NULL);
	id_of(&herd, jstr(k, "herd_id"));
	id_of(&collar, jstr(k, "collar_id"));
	slots_set_herd(&s, &herd);
	slots_set_collar(&s, &collar);

	for (size_t i = 0; i < steps->n; i++) {
		const struct jval *st = &steps->items[i];
		const struct jval *ex = &expect->items[i];
		const char *op = jstr(st, "op");
		struct slot_ack ack;
		int acks = 0;
		int64_t now = 0, eff = 0;
		bool has_now = time_of(st, "now", &now);

		if (strcmp(op, "insert") == 0) {
			const char *h = jstr(st, "herd_id");
			const struct jval *vx = jget(st, "vertices");
			bool has_eff = time_of(st, "effective_at", &eff);

			fx_command(&cmd, cmd_buf, (uint32_t)jnum(st, "version"),
				   h ? h : jstr(k, "herd_id"), jstr(st, "collar_id"), has_eff, eff,
				   vx ? (int)vx->num : 4, &lim);
			ack = slots_insert(&s, &cmd, has_now, now);
			acks = 1;
		} else if (strcmp(op, "tick") == 0) {
			acks = slots_tick(&s, now, &ack) ? 1 : 0;
		} else if (strcmp(op, "boot") == 0) {
			store_ram_reboot();
			applied.calls = 0;
			slots_load(&s);
			/* The active boundary is enforced at once, from flash */
			CHECK_CASE(slots_active(&s) == NULL || applied.calls == 1, name,
				   "boot applies the active boundary");
		} else {
			CHECK_CASE(false, name, "unknown op %s", op);
		}

		const struct jval *want_acks = jget(ex, "acks");

		CHECK_CASE((size_t)acks == want_acks->n, name, "step %zu: %d acks", i, acks);
		if (acks == 1 && want_acks->n == 1) {
			check_ack(name, i, &ack, &want_acks->items[0]);
		}

		const struct jval *act = jget(ex, "active");
		const struct slot_hdr *a = slots_active(&s);
		const struct jval *fb = jget(ex, "free_bytes");
		uint32_t free_bytes = 0;
		bool has_fb = slots_free_bytes(&s, &free_bytes);

		if (act->t == J_NULL) {
			CHECK_CASE(a == NULL, name, "step %zu: active %u, want none", i,
				   a ? (unsigned)a->version : 0);
		} else {
			CHECK_CASE(a && a->version == (uint32_t)act->num, name,
				   "step %zu: active %u, want %u", i, a ? (unsigned)a->version : 0,
				   (unsigned)act->num);
			/* The fence was given the same boundary */
			CHECK_CASE(a && applied.version == a->version && applied.total == a->total,
				   name, "step %zu: applied %u", i, (unsigned)applied.version);
		}
		CHECK_CASE(slots_have(&s) == (uint32_t)jnum(ex, "have"), name, "step %zu: have %u",
			   i, (unsigned)slots_have(&s));
		CHECK_CASE(slots_free(&s) == (uint32_t)jnum(ex, "free"), name, "step %zu: free %u",
			   i, (unsigned)slots_free(&s));
		if (fb->t == J_NULL) {
			CHECK_CASE(!has_fb, name, "step %zu: free_bytes should be unknown", i);
		} else {
			CHECK_CASE(has_fb && free_bytes == (uint32_t)fb->num, name,
				   "step %zu: free_bytes %u, want %u", i, (unsigned)free_bytes,
				   (unsigned)fb->num);
		}

		/* Whatever the step did is on flash: a reboot now gives the same state */
		{
			static struct slots again;
			uint32_t fb2 = 0;

			slots_init(&again, &lim, scratch, NULL, NULL);
			slots_load(&again);
			CHECK_CASE(slots_have(&again) == slots_have(&s) &&
					   slots_free(&again) == slots_free(&s) &&
					   (slots_active(&again) == NULL) == (a == NULL) &&
					   slots_free_bytes(&again, &fb2) == has_fb && fb2 == free_bytes,
				   name, "step %zu: state after a reboot differs", i);
		}
	}
}

static void test_vectors(void)
{
	struct jval *f = json_load(VECTORS "/slots.json");
	const struct jval *cases = jget(f, "cases");

	for (size_t c = 0; c < cases->n; c++) {
		run_case(&cases->items[c]);
	}
	printf("slots.json: %zu cases\n", cases->n);
}

static void test_record_round_trip(void)
{
	static struct boundary_cmd cmd;
	static uint8_t rec[SLOT_RECORD_MAX];
	static int32_t back[SHAPE_BUF_VERTICES][2];
	struct slot_hdr h = {0}, d;

	fx_command(&cmd, cmd_buf, 7, "herd_1", NULL, true, 1790510400, 384, &LIMITS_V0);
	h.version = 7;
	h.flags = SLOT_F_HERD | SLOT_F_EFFECTIVE | SLOT_F_TRACK;
	h.rings = (uint8_t)cmd.shape.rings;
	for (int k = 0; k < h.rings; k++) {
		h.ring_len[k] = cmd.shape.len[k];
	}
	h.total = (uint16_t)cmd.shape.total;
	h.effective_at = 1790510400;
	h.warn_m = 4.5;
	h.hysteresis_m = 0.75;
	h.command_id = cmd.command_id;
	h.herd_id = cmd.herd_id;

	uint32_t len = slot_encode(&h, (const int32_t(*)[2])cmd_buf, rec);

	CHECK(len == 192 + 8 * 384 && len == SLOT_RECORD_MAX);
	CHECK(slot_decode(rec, len, &d, back));
	CHECK(d.version == 7 && d.flags == h.flags && d.rings == 9 && d.total == 384);
	CHECK(d.effective_at == h.effective_at && d.warn_m == 4.5 && d.hysteresis_m == 0.75);
	CHECK(strcmp(d.command_id.s, "bnd_v7") == 0 && strcmp(d.herd_id.s, "herd_1") == 0);
	CHECK(memcmp(back, cmd_buf, 384 * sizeof(back[0])) == 0);

	/* Any flipped byte fails the CRC or the format */
	int caught = 0;

	for (uint32_t i = 0; i < len; i++) {
		rec[i] ^= 0x10;
		caught += !slot_decode(rec, len, &d, back);
		rec[i] ^= 0x10;
	}
	CHECK(caught == (int)len);
	CHECK(!slot_decode(rec, len - 1, &d, back));
	rec[4] = 2; /* A format this firmware doesn't know */
	CHECK(!slot_decode(rec, len, &d, back));
}

int main(void)
{
	test_vectors();
	test_record_round_trip();
	return test_done("slots");
}
