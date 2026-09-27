/* Commands as the collar receives them: commands.json, canonical bytes, value tokens */
#include "../../src/command.h"
#include "json.h"
#include "test.h"

struct buf {
	char b[PROTO_MAX_COMMAND_BYTES + 64];
	size_t n;
};

static void buf_sink(void *ctx, const uint8_t *p, size_t n)
{
	struct buf *b = ctx;

	memcpy(b->b + b->n, p, n);
	b->n += n;
}

static void load_key(const struct jval *f, uint8_t key[32])
{
	const char *pk = jstr(f, "public_key");

	CHECK(proto_base64_decode(pk, strlen(pk), key, 32) == 32);
}

static void test_vectors(void)
{
	static int32_t v[SHAPE_BUF_VERTICES][2];
	static struct buf canon;
	static struct boundary_cmd cmd;
	struct jval *f = json_load(VECTORS "/commands.json");
	const struct jval *cases = jget(f, "cases");
	uint8_t key[32];
	int n = 0;

	load_key(f, key);
	CHECK(jnum(f, "max_bytes") == PROTO_MAX_COMMAND_BYTES);
	CHECK(jnum(f, "max_keys") == PROTO_MAX_KEYS);

	for (size_t c = 0; c < cases->n; c++) {
		const struct jval *k = &cases->items[c];
		const char *name = jstr(k, "name");
		const struct jval *wire = jget(k, "wire");
		enum reject_code got =
			command_parse(wire->str, wire->str_len, key, &cmd, v, SHAPE_BUF_VERTICES);
		const char *want = jbool(k, "valid") ? "" : jstr(k, "code");

		CHECK_CASE(strcmp(reject_str(got), want) == 0, name, "got '%s', want '%s'",
			   reject_str(got), want);

		const char *canonical = jstr(k, "canonical");

		if (canonical) {
			struct wire_scan sc;

			CHECK_CASE(wire_scan(wire->str, wire->str_len, &sc) == REJECT_NONE, name,
				   "scans");
			canon.n = 0;
			wire_canonical(wire->str, &sc, buf_sink, &canon);
			CHECK_CASE(canon.n == strlen(canonical) &&
					   memcmp(canon.b, canonical, canon.n) == 0,
				   name, "canonical bytes differ");
		}
		n++;
	}
	CHECK(n >= 30);
	printf("commands.json: %d cases\n", n);
}

/* What the valid vectors carry, read back field by field */
static void test_fields(void)
{
	static int32_t v[SHAPE_BUF_VERTICES][2];
	static struct boundary_cmd cmd;
	struct jval *f = json_load(VECTORS "/commands.json");
	const struct jval *cases = jget(f, "cases");
	uint8_t key[32];

	load_key(f, key);
	for (size_t c = 0; c < cases->n; c++) {
		const struct jval *k = &cases->items[c];
		const char *name = jstr(k, "name");
		const struct jval *wire = jget(k, "wire");

		if (strcmp(name, "v0_compact") == 0) {
			CHECK(command_parse(wire->str, wire->str_len, key, &cmd, v,
					    SHAPE_BUF_VERTICES) == REJECT_NONE);
			CHECK(strcmp(cmd.command_id.s, "bnd_01J8V0GOLDEN") == 0);
			CHECK(cmd.has_herd && strcmp(cmd.herd_id.s, "herd_01J7GOLDEN") == 0);
			CHECK(!cmd.has_collar && cmd.version == 57 && !cmd.track);
			CHECK(cmd.has_effective_at && cmd.effective_at == 1790510400); /* 2026-09-27T12:00:00Z */
			CHECK(cmd.has_warn && cmd.warn_m == 5.0 && cmd.has_hysteresis &&
			      cmd.hysteresis_m == 1.0);
			CHECK(cmd.shape.rings == 1 && cmd.shape.len[0] == 4);
			CHECK(v[0][0] == -924100000 && v[0][1] == 381200000);
			CHECK(v[1][0] == -924000000 && v[2][1] == 381300000);
		}
		if (strcmp(name, "holes_collar_id_track") == 0) {
			CHECK(command_parse(wire->str, wire->str_len, key, &cmd, v,
					    SHAPE_BUF_VERTICES) == REJECT_NONE);
			CHECK(cmd.has_collar && strcmp(cmd.collar_id.s, "col_01J9SIMCOLLAR") == 0);
			CHECK(cmd.track && cmd.version == 58);
			CHECK(cmd.shape.rings == 3 && cmd.shape.total == 12);
			CHECK(shape_check(&cmd.shape, &LIMITS_V0, cmd.warn_m, cmd.hysteresis_m, 0) ==
			      REJECT_NONE);
		}
		if (strcmp(name, "exponent_1e-7") == 0) {
			CHECK(command_parse(wire->str, wire->str_len, key, &cmd, v,
					    SHAPE_BUF_VERTICES) == REJECT_NONE);
			CHECK(v[0][0] == 1 && v[0][1] == 0);
			CHECK(!cmd.has_warn && cmd.has_hysteresis && cmd.hysteresis_m == 0.0);
		}
		if (strcmp(name, "v0_no_herd_no_margins") == 0) {
			CHECK(command_parse(wire->str, wire->str_len, key, &cmd, v,
					    SHAPE_BUF_VERTICES) == REJECT_NONE);
			CHECK(!cmd.has_herd && !cmd.has_warn && !cmd.has_effective_at);
		}
	}
}

static void test_tokens(void)
{
	char out[80];
	size_t len;
	uint32_t u;
	double d;

	CHECK(wire_string("\"abc\"", 5, out, sizeof(out), &len) && len == 3 &&
	      memcmp(out, "abc", 3) == 0);
	CHECK(wire_string("\"a\\u0062\\n\\\"\"", 13, out, sizeof(out), &len) && len == 4 &&
	      memcmp(out, "ab\n\"", 4) == 0);
	CHECK(wire_string("\"\\ud83d\\ude00\"", 14, out, sizeof(out), &len) && len == 4 &&
	      (uint8_t)out[0] == 0xf0);
	CHECK(!wire_string("\"\\ud83d\"", 8, out, sizeof(out), &len)); /* Lone surrogate */
	CHECK(!wire_string("\"\\ude00\"", 8, out, sizeof(out), &len));
	CHECK(!wire_string("12", 2, out, sizeof(out), &len));
	/* Longer than cap: the full length is still reported */
	CHECK(wire_string("\"abcdef\"", 8, out, 3, &len) && len == 6);

	CHECK(wire_u32("0", 1, &u) && u == 0);
	CHECK(wire_u32("-0", 2, &u) && u == 0);
	CHECK(wire_u32("4294967295", 10, &u) && u == 4294967295u);
	CHECK(!wire_u32("4294967296", 10, &u));
	CHECK(!wire_u32("-1", 2, &u));
	CHECK(!wire_u32("5.0", 3, &u));
	CHECK(!wire_u32("5e1", 3, &u));
	CHECK(!wire_u32("\"5\"", 3, &u));

	CHECK(wire_f64("5.0,", 3, &d) && d == 5.0);
	CHECK(wire_f64("-0.25]", 5, &d) && d == -0.25);
	CHECK(wire_f64("1e3}", 3, &d) && d == 1000.0);
	CHECK(!wire_f64("1e999}", 5, &d));
	CHECK(!wire_f64("null", 4, &d));
}

static void test_scanner_rules(void)
{
	struct wire_scan sc;
	const char *bad[] = {
		"[1,2]", "{\"a\":1} x", "{\"a\":01}", "{\"a\":1.}", "{\"a\":\"x\ny\"}",
		"{\"a\":\"\\q\"}", "{\"\\u0061\":1}", "{\"a\":[[[[[1]]]]]}", "{\"a\":1,\"a\":1}",
		"{\"a\":{\"b\":1}}", "{\"a\":[{\"b\":1}]}", "{\"a\":tru}", "{\"a\":1,}", "{",
	};

	for (size_t i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) {
		CHECK_CASE(wire_scan(bad[i], strlen(bad[i]), &sc) == REJECT_BAD_JSON, bad[i],
			   "should be bad_json");
	}
	CHECK(wire_scan("{\"a\":[[[[1]]]]}", 15, &sc) == REJECT_NONE);
	CHECK(wire_scan("{}", 2, &sc) == REJECT_NONE && sc.n == 0 && sc.sig == -1);

	const char bad_utf8[] = {'{', '"', 'a', '"', ':', '"', (char)0xff, '"', '}'};
	const char overlong[] = {'{', '"', 'a', '"', ':', '"', (char)0xc0, (char)0x80, '"', '}'};
	const char surrogate[] = {'{', '"', 'a', '"', ':', '"', (char)0xed, (char)0xa0, (char)0x80,
				  '"', '}'};
	const char good[] = {'{', '"', 'a', '"', ':', '"', (char)0xc3, (char)0xa9, '"', '}'};

	CHECK(wire_scan(bad_utf8, sizeof(bad_utf8), &sc) == REJECT_BAD_JSON);
	CHECK(wire_scan(overlong, sizeof(overlong), &sc) == REJECT_BAD_JSON);
	CHECK(wire_scan(surrogate, sizeof(surrogate), &sc) == REJECT_BAD_JSON);
	CHECK(wire_scan(good, sizeof(good), &sc) == REJECT_NONE);

	/* Canonical: keys sorted by bytes, sig left out, whitespace outside strings gone */
	static struct buf b;
	const char *w = " { \"b\" : [ 1 , \"x y\" ] ,\n \"a\" : 1e-7 , \"sig\":\"s\" } ";

	CHECK(wire_scan(w, strlen(w), &sc) == REJECT_NONE && sc.sig == 2);
	b.n = 0;
	wire_canonical(w, &sc, buf_sink, &b);
	CHECK(b.n == strlen("{\"a\":1e-7,\"b\":[1,\"x y\"]}") &&
	      memcmp(b.b, "{\"a\":1e-7,\"b\":[1,\"x y\"]}", b.n) == 0);

	/* A key that is a prefix of another sorts first */
	w = "{\"ab\":1,\"a\":2}";
	CHECK(wire_scan(w, strlen(w), &sc) == REJECT_NONE);
	b.n = 0;
	wire_canonical(w, &sc, buf_sink, &b);
	CHECK(b.n == 14 && memcmp(b.b, "{\"a\":2,\"ab\":1}", 14) == 0);
}

int main(void)
{
	test_vectors();
	test_fields();
	test_tokens();
	test_scanner_rules();
	return test_done("command");
}
