#include "welfare_store.h"

#include <string.h>

#include "protocol.h"
#include "store.h"

#define WELFARE_MAGIC 0x3157434fu /* "OCW1" */
#define WELFARE_FORMAT 1

#define F_OFF 0x01
#define F_SHUTOFF_AT 0x02
#define F_WINDOW 0x04

#define OFF_SEQ 8
#define OFF_SHUTOFF 12
#define OFF_WINDOW 20
#define OFF_CRC 28
#define WELFARE_BYTES (OFF_CRC + 4)

static uint8_t buf[WELFARE_BYTES];

static void put32(uint8_t *p, uint32_t v)
{
	for (int k = 0; k < 4; k++) {
		p[k] = (uint8_t)(v >> (8 * k));
	}
}

static uint32_t get32(const uint8_t *p)
{
	return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 |
	       (uint32_t)p[3] << 24;
}

static void put64(uint8_t *p, int64_t v)
{
	put32(p, (uint32_t)v);
	put32(p + 4, (uint32_t)((uint64_t)v >> 32));
}

static int64_t get64(const uint8_t *p)
{
	return (int64_t)((uint64_t)get32(p) | (uint64_t)get32(p + 4) << 32);
}

void welfare_store_init(struct welfare_store *w)
{
	memset(w, 0, sizeof(*w));
}

static int write_record(const struct welfare_store *w)
{
	uint8_t flags = 0;

	memset(buf, 0, sizeof(buf));
	flags |= w->enforcement_off ? F_OFF : 0;
	flags |= w->has_shutoff_at ? F_SHUTOFF_AT : 0;
	flags |= w->has_window_start ? F_WINDOW : 0;
	put32(buf, WELFARE_MAGIC);
	buf[4] = WELFARE_FORMAT;
	buf[5] = flags;
	buf[6] = w->escape_cycles;
	put32(buf + OFF_SEQ, w->rearm_seq);
	put64(buf + OFF_SHUTOFF, w->shutoff_at);
	put64(buf + OFF_WINDOW, w->window_start);
	put32(buf + OFF_CRC, proto_crc32(0, buf, OFF_CRC));
	return store_write(STORE_ID_WELFARE, buf, WELFARE_BYTES);
}

void welfare_store_load(struct welfare_store *w)
{
	int len = store_read(STORE_ID_WELFARE, buf, sizeof(buf));
	struct welfare_store t;
	uint8_t flags;

	welfare_store_init(w);
	if (len != WELFARE_BYTES || get32(buf) != WELFARE_MAGIC || buf[4] != WELFARE_FORMAT ||
	    get32(buf + OFF_CRC) != proto_crc32(0, buf, OFF_CRC)) {
		return;
	}
	flags = buf[5];
	welfare_store_init(&t);
	t.enforcement_off = (flags & F_OFF) != 0;
	t.has_shutoff_at = (flags & F_SHUTOFF_AT) != 0;
	t.has_window_start = (flags & F_WINDOW) != 0;
	t.escape_cycles = buf[6];
	t.rearm_seq = get32(buf + OFF_SEQ);
	t.shutoff_at = get64(buf + OFF_SHUTOFF);
	t.window_start = get64(buf + OFF_WINDOW);
	*w = t;
}

int welfare_store_save(struct welfare_store *w)
{
	struct welfare_store held;

	/* Never lower the persisted rearm_seq, even if the caller asks. */
	welfare_store_load(&held);
	if (w->rearm_seq < held.rearm_seq) {
		w->rearm_seq = held.rearm_seq;
	}
	if (write_record(w) != 0) {
		w->store_errors++;
		return -1;
	}
	return 0;
}

void welfare_store_clear_shutoff(struct welfare_store *w)
{
	w->enforcement_off = false;
	w->has_shutoff_at = false;
	w->shutoff_at = 0;
	w->escape_cycles = 0;
	w->has_window_start = false;
	w->window_start = 0;
	(void)welfare_store_save(w);
}

void welfare_store_accept_rearm(struct welfare_store *w, uint32_t rearm_seq)
{
	if (rearm_seq > w->rearm_seq) {
		w->rearm_seq = rearm_seq;
	}
	welfare_store_clear_shutoff(w);
}

void welfare_store_wipe_shutoff_keep_seq(struct welfare_store *w)
{
	uint32_t seq = w->rearm_seq;

	welfare_store_init(w);
	w->rearm_seq = seq;
	(void)welfare_store_save(w);
}
