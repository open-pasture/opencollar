#include "provision.h"

#include <string.h>

#include "command.h"
#include "store.h"

static char buf[PROVISION_MAX_BYTES];

const char *prov_error_str(enum prov_error e)
{
	switch (e) {
	case PROV_OK:
		return "ok";
	case PROV_BAD_JSON:
		return "bad_json";
	case PROV_BAD_VERSION:
		return "bad_version";
	case PROV_BAD_COLLAR_ID:
		return "bad_collar_id";
	case PROV_BAD_HERD_ID:
		return "bad_herd_id";
	case PROV_BAD_KEY:
		return "bad_key";
	case PROV_BAD_ENDPOINT:
		return "bad_endpoint";
	case PROV_BAD_SERVER_KEY:
		return "bad_server_key";
	case PROV_STORE_FAILED:
		return "store_failed";
	}
	return "";
}

/* A string field decoded into out (cap bytes plus a NUL); false if absent or not a string */
static bool field(const char *w, const struct wire_scan *sc, const char *key, char *out,
		  size_t cap, size_t *len)
{
	const struct wire_span *sp = wire_find(w, sc, key);

	if (!sp || !wire_string(w + sp->val, sp->val_len, out, cap, len)) {
		return false;
	}
	out[*len < cap ? *len : cap] = '\0';
	return true;
}

enum prov_error provision_parse(const char *json, size_t len, struct provision *out)
{
	struct wire_scan sc;
	struct provision p;
	const struct wire_span *sp;
	uint32_t v;
	char tmp[PROTO_MAX_ENDPOINT_BYTES + 1];
	size_t n;

	memset(out, 0, sizeof(*out));
	memset(&p, 0, sizeof(p));
	if (len > PROVISION_MAX_BYTES || wire_scan(json, len, &sc) != REJECT_NONE) {
		return PROV_BAD_JSON;
	}

	sp = wire_find(json, &sc, "v");
	if (!sp || !wire_u32(json + sp->val, sp->val_len, &v) || v != 1) {
		return PROV_BAD_VERSION;
	}
	if (!wire_read_id(json, wire_find(json, &sc, "c"), false, NULL, &p.collar_id)) {
		return PROV_BAD_COLLAR_ID;
	}
	if (!wire_read_id(json, wire_find(json, &sc, "h"), false, NULL, &p.herd_id)) {
		return PROV_BAD_HERD_ID;
	}

	if (!field(json, &sc, "k", p.key, PROVISION_KEY_MAX, &n) || n < PROVISION_KEY_MIN ||
	    n > PROVISION_KEY_MAX) {
		return PROV_BAD_KEY;
	}
	for (size_t i = 0; i < n; i++) {
		if (p.key[i] < 0x21 || p.key[i] > 0x7e) {
			return PROV_BAD_KEY;
		}
	}

	if (!field(json, &sc, "e", p.endpoint, PROTO_MAX_ENDPOINT_BYTES, &n) ||
	    n > PROTO_MAX_ENDPOINT_BYTES || n <= 8 || memcmp(p.endpoint, "https://", 8) != 0 ||
	    memchr(p.endpoint, '\0', n) != NULL) {
		return PROV_BAD_ENDPOINT;
	}

	if (!field(json, &sc, "s", tmp, sizeof(tmp) - 1, &n) || n >= sizeof(tmp) ||
	    proto_base64_decode(tmp, n, p.server_key, sizeof(p.server_key)) != 32) {
		return PROV_BAD_SERVER_KEY;
	}

	p.ok = true;
	*out = p;
	return PROV_OK;
}

void provision_load(struct provision *out)
{
	int len = store_read(STORE_ID_PROVISION, buf, sizeof(buf));

	memset(out, 0, sizeof(*out));
	if (len <= 0 || len > (int)sizeof(buf)) {
		return;
	}
	provision_parse(buf, (size_t)len, out);
}

int provision_save(const char *json, size_t len)
{
	return store_write(STORE_ID_PROVISION, json, len);
}
