/* Shape rules: shapes.json, and the exact decimal to e7 conversion they rest on */
#include "../../src/command.h"
#include "../../src/shape.h"
#include "json.h"
#include "test.h"

static bool feed_ring(struct shape *s, const struct jval *ring)
{
	shape_ring_begin(s);
	for (size_t i = 0; i < ring->n; i++) {
		const struct jval *p = &ring->items[i];
		int64_t lon, lat;
		bool a, b;

		if (!wire_e7(p->items[0].raw, p->items[0].raw_len, 1800000000, &lon, &a) ||
		    !wire_e7(p->items[1].raw, p->items[1].raw_len, 900000000, &lat, &b)) {
			return false;
		}
		shape_vertex(s, lon, lat, a && b);
	}
	shape_ring_end(s);
	return true;
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

static void test_vectors(void)
{
	static int32_t buf[SHAPE_BUF_VERTICES][2];
	struct jval *f = json_load(VECTORS "/shapes.json");
	const struct jval *cases = jget(f, "cases");
	double slack = jnum(f, "slack_m");
	bool seen[REJECT_COUNT] = {false};
	int n = 0;

	for (size_t c = 0; c < cases->n; c++) {
		const struct jval *k = &cases->items[c];
		const char *name = jstr(k, "name");
		const struct jval *holes = jget(k, "holes");
		struct collar_limits lim = limits_of(jget(k, "limits"));
		struct shape s;
		bool ok;

		shape_init(&s, buf, SHAPE_BUF_VERTICES);
		ok = feed_ring(&s, jget(k, "boundary"));
		for (size_t h = 0; ok && holes && h < holes->n; h++) {
			ok = feed_ring(&s, &holes->items[h]);
		}
		CHECK_CASE(ok, name, "numbers read");

		enum reject_code got =
			shape_check(&s, &lim, jnum(k, "warn_m"), jnum(k, "hysteresis_m"), slack);
		const char *want = jbool(k, "ok") ? "" : jstr(k, "code");

		CHECK_CASE(strcmp(reject_str(got), want) == 0, name, "got '%s', want '%s'",
			   reject_str(got), want);
		seen[got] = true;
		n++;
	}

	/* Every shape code has a case */
	for (int code = REJECT_OUT_OF_RANGE; code <= REJECT_BAD_MARGINS; code++) {
		CHECK_CASE(seen[code], reject_str((enum reject_code)code), "no case");
	}
	printf("shapes.json: %d cases\n", n);
}

static void e7(const char *text, int64_t want, bool want_in_range)
{
	int64_t got;
	bool in_range;

	CHECK_CASE(wire_e7(text, strlen(text), 1800000000, &got, &in_range), text, "parses");
	CHECK_CASE(got == want, text, "e7 %lld, want %lld", (long long)got, (long long)want);
	CHECK_CASE(in_range == want_in_range, text, "in range %d", in_range);
}

static void test_decimal_to_e7(void)
{
	e7("-92.41", -924100000, true);
	e7("38.1234567", 381234567, true);
	e7("1e-7", 1, true);
	e7("1E-7", 1, true);
	e7("5e-8", 1, true);   /* Half away from zero */
	e7("-5e-8", -1, true);
	e7("4.9e-8", 0, true);
	e7("0.00000005", 1, true);
	e7("0.000000049999", 0, true);
	e7("180", 1800000000, true);
	e7("180.0000000", 1800000000, true);
	e7("-180.0", -1800000000, true);
	e7("180.00000001", 1800000000, false); /* Rounds to 180 but is over it */
	e7("180.0000001", 1800000001, false);
	e7("1.8e2", 1800000000, true);
	e7("0.0018e5", 1800000000, true);
	e7("-0", 0, true);
	e7("0.0", 0, true);
	e7("1e20", 0, false);
	e7("12345678901234567890", 0, false);
	e7("1e-400", 0, true);

	int64_t v;
	bool r;

	CHECK(!wire_e7("1e400", 5, 1800000000, &v, &r)); /* Not a double */
	CHECK(!wire_e7("\"1\"", 3, 1800000000, &v, &r));
	CHECK(!wire_e7("1.", 2, 1800000000, &v, &r));
	CHECK(!wire_e7("", 0, 1800000000, &v, &r));
}

static void test_cleaning_and_counts(void)
{
	static int32_t buf[SHAPE_BUF_VERTICES][2];
	struct shape s;

	/* Consecutive duplicates and a closing vertex are not counted */
	shape_init(&s, buf, SHAPE_BUF_VERTICES);
	shape_ring_begin(&s);
	shape_vertex(&s, 0, 0, true);
	shape_vertex(&s, 0, 0, true);
	shape_vertex(&s, 100000, 0, true);
	shape_vertex(&s, 100000, 100000, true);
	shape_vertex(&s, 0, 100000, true);
	shape_vertex(&s, 0, 0, true);
	shape_ring_end(&s);
	CHECK(s.len[0] == 4 && s.total == 4 && s.stored == 4);
	CHECK(shape_check(&s, &LIMITS_V0, 5, 1, 0) == REJECT_NONE);

	/* More holes than any limit: counted, not stored */
	shape_init(&s, buf, SHAPE_BUF_VERTICES);
	for (int k = 0; k < 20; k++) {
		shape_ring_begin(&s);
		shape_vertex(&s, k, 0, true);
		shape_ring_end(&s);
	}
	CHECK(s.rings == 20);
	CHECK(shape_check(&s, &LIMITS_V0, 5, 1, 0) == REJECT_TOO_MANY_HOLES);

	/* More vertices than the storage: too_many_vertices, never a crash */
	shape_init(&s, buf, SHAPE_BUF_VERTICES);
	shape_ring_begin(&s);
	for (int i = 0; i < 1000; i++) {
		shape_vertex(&s, i * 1000, (i % 2) * 1000, true);
	}
	shape_ring_end(&s);
	CHECK(s.overflow && s.total == 1000);
	CHECK(shape_check(&s, &LIMITS_V0, 5, 1, 0) == REJECT_TOO_MANY_VERTICES);

	/* An out-of-range vertex decides the code even after a bad ring count */
	shape_init(&s, buf, SHAPE_BUF_VERTICES);
	shape_ring_begin(&s);
	shape_vertex(&s, 0, 0, false);
	shape_ring_end(&s);
	CHECK(shape_check(&s, &LIMITS_V0, 5, 1, 0) == REJECT_OUT_OF_RANGE);
	CHECK(shape_check(&s, &LIMITS_V0, NAN, 1, 0) == REJECT_BAD_MARGINS);
	CHECK(shape_check(&s, &LIMITS_V0, 5, INFINITY, 0) == REJECT_BAD_MARGINS);
}

int main(void)
{
	test_vectors();
	test_decimal_to_e7();
	test_cleaning_and_counts();
	return test_done("shape");
}
