#include "acks.h"

#include <string.h>

#include "store.h"

#define ACKS_MAGIC 0x314b434fu /* "OCK1" */
/* version, status, code, has_at, id length, at (8), id (64) */
#define ACK_BYTES (4 + 4 + 8 + PROTO_MAX_ID_BYTES)
#define ACKS_BYTES (8 + ACKS_MAX * ACK_BYTES + 4)

static uint8_t buf[ACKS_BYTES];

static void put32(uint8_t *p, uint32_t v)
{
	for (int k = 0; k < 4; k++) {
		p[k] = (uint8_t)(v >> (8 * k));
	}
}

static uint32_t get32(const uint8_t *p)
{
	return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static int save(const struct acks *a)
{
	uint8_t *p = buf + 8;
	size_t len;

	if (a->n == 0) {
		return store_delete(STORE_ID_ACKS);
	}
	put32(buf, ACKS_MAGIC);
	buf[4] = a->n;
	buf[5] = buf[6] = buf[7] = 0;
	for (int i = 0; i < a->n; i++) {
		const struct slot_ack *k = &a->q[i];

		memset(p, 0, ACK_BYTES);
		put32(p, k->version);
		p[4] = k->status;
		p[5] = k->code;
		p[6] = k->has_at;
		p[7] = k->command_id.len;
		put32(p + 8, (uint32_t)k->at);
		put32(p + 12, (uint32_t)((uint64_t)k->at >> 32));
		memcpy(p + 16, k->command_id.s, k->command_id.len);
		p += ACK_BYTES;
	}
	len = (size_t)(p - buf);
	put32(p, proto_crc32(0, buf, len));
	return store_write(STORE_ID_ACKS, buf, len + 4);
}

void acks_load(struct acks *a)
{
	int len = store_read(STORE_ID_ACKS, buf, sizeof(buf));

	memset(a, 0, sizeof(*a));
	if (len < 12 || len > (int)sizeof(buf) || get32(buf) != ACKS_MAGIC || buf[4] > ACKS_MAX ||
	    len != 8 + buf[4] * ACK_BYTES + 4 ||
	    get32(buf + len - 4) != proto_crc32(0, buf, (size_t)len - 4)) {
		return;
	}
	for (int i = 0; i < buf[4]; i++) {
		const uint8_t *p = buf + 8 + i * ACK_BYTES;
		struct slot_ack *k = &a->q[a->n];

		if (!proto_id_set(&k->command_id, (const char *)p + 16, p[7])) {
			continue;
		}
		k->version = get32(p);
		k->status = p[4];
		k->code = p[5];
		k->has_at = p[6] != 0;
		k->at = (int64_t)((uint64_t)get32(p + 8) | (uint64_t)get32(p + 12) << 32);
		a->n++;
	}
}

int acks_push(struct acks *a, const struct slot_ack *ack)
{
	if (a->n == ACKS_MAX) {
		memmove(&a->q[0], &a->q[1], (ACKS_MAX - 1) * sizeof(a->q[0]));
		a->n--;
	}
	a->q[a->n++] = *ack;
	return save(a);
}

const struct slot_ack *acks_peek(const struct acks *a)
{
	return a->n > 0 ? &a->q[0] : NULL;
}

int acks_pop(struct acks *a)
{
	if (a->n == 0) {
		return 0;
	}
	memmove(&a->q[0], &a->q[1], (size_t)(a->n - 1) * sizeof(a->q[0]));
	a->n--;
	return save(a);
}

int acks_clear(struct acks *a)
{
	a->n = 0;
	return store_delete(STORE_ID_ACKS);
}
