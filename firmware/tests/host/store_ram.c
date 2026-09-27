#include "store_ram.h"

#include <errno.h>
#include <string.h>

#include "../../src/store.h"

#define HDR 4 /* id (2), length (2) */
#define COMMIT 0x00
#define ERASED 0xff

static uint8_t flash[STORE_RAM_BYTES];
static size_t head;
static long budget = -1;
static bool cut;
static size_t written;

void store_ram_reset(void)
{
	memset(flash, ERASED, sizeof(flash));
	head = 0;
	budget = -1;
	cut = false;
	written = 0;
}

void store_ram_cut_after(long n)
{
	budget = n;
}

bool store_ram_is_cut(void)
{
	return cut;
}

size_t store_ram_written(void)
{
	return written;
}

/* Walk the log: calls fn for each committed entry; returns where the log ends */
static size_t walk(void (*fn)(size_t at, uint16_t id, uint16_t len, void *ctx), void *ctx)
{
	size_t at = 0;

	while (at + HDR <= sizeof(flash)) {
		uint16_t id = (uint16_t)(flash[at] | flash[at + 1] << 8);
		uint16_t len = (uint16_t)(flash[at + 2] | flash[at + 3] << 8);

		if (id == 0xffff) {
			break; /* Erased: the end */
		}
		if (at + HDR + len + 1 > sizeof(flash) || flash[at + HDR + len] != COMMIT) {
			break; /* Unfinished entry */
		}
		if (fn) {
			fn(at, id, len, ctx);
		}
		at += HDR + len + 1;
	}
	return at;
}

void store_ram_reboot(void)
{
	size_t end = walk(NULL, NULL);

	/* The unfinished tail is dropped (NVS moves past it) */
	memset(flash + end, ERASED, sizeof(flash) - end);
	head = end;
	budget = -1;
	cut = false;
}

struct find {
	uint16_t id;
	long at;
	uint16_t len;
};

static void find_fn(size_t at, uint16_t id, uint16_t len, void *ctx)
{
	struct find *f = ctx;

	if (id == f->id) {
		f->at = (long)at;
		f->len = len;
	}
}

static bool latest(uint16_t id, size_t *at, uint16_t *len)
{
	struct find f = {.id = id, .at = -1};

	walk(find_fn, &f);
	if (f.at < 0 || f.len == 0) {
		return false; /* None, or deleted (an empty entry) */
	}
	*at = (size_t)f.at + HDR;
	*len = f.len;
	return true;
}

static bool put(uint8_t b)
{
	if (cut) {
		return false;
	}
	if (budget == 0) {
		cut = true;
		return false;
	}
	if (budget > 0) {
		budget--;
	}
	flash[head++] = b;
	written++;
	return true;
}

/* Keep only live entries (not tested under power cuts) */
static void compact(void)
{
	static uint8_t copy[STORE_RAM_BYTES];
	size_t n = 0;
	size_t end = walk(NULL, NULL);

	for (size_t at = 0; at < end;) {
		uint16_t id = (uint16_t)(flash[at] | flash[at + 1] << 8);
		uint16_t len = (uint16_t)(flash[at + 2] | flash[at + 3] << 8);
		size_t lat;
		uint16_t llen;

		if (latest(id, &lat, &llen) && lat == at + HDR) {
			memcpy(copy + n, flash + at, HDR + len + 1u);
			n += HDR + len + 1u;
		}
		at += HDR + len + 1u;
	}
	memset(flash, ERASED, sizeof(flash));
	memcpy(flash, copy, n);
	head = n;
}

static int append(uint16_t id, const void *buf, size_t len)
{
	const uint8_t *p = buf;

	if (cut) {
		return -EIO;
	}
	if (head + HDR + len + 1 > sizeof(flash)) {
		compact();
		if (head + HDR + len + 1 > sizeof(flash)) {
			return -ENOSPC;
		}
	}
	if (!put((uint8_t)id) || !put((uint8_t)(id >> 8)) || !put((uint8_t)len) ||
	    !put((uint8_t)(len >> 8))) {
		return -EIO;
	}
	for (size_t i = 0; i < len; i++) {
		if (!put(p[i])) {
			return -EIO;
		}
	}
	return put(COMMIT) ? 0 : -EIO;
}

int store_init(void)
{
	store_ram_reboot();
	return 0;
}

int store_read(uint16_t id, void *buf, size_t cap)
{
	size_t at;
	uint16_t len;

	if (!latest(id, &at, &len)) {
		return -ENOENT;
	}
	memcpy(buf, flash + at, len < cap ? len : cap);
	return len;
}

int store_write(uint16_t id, const void *buf, size_t len)
{
	if (len == 0 || len > 0xfffe) {
		return -EINVAL;
	}
	return append(id, buf, len);
}

int store_delete(uint16_t id)
{
	size_t at;
	uint16_t len;

	if (!latest(id, &at, &len)) {
		return 0;
	}
	return append(id, NULL, 0);
}

bool store_ram_corrupt(uint16_t id, size_t offset)
{
	size_t at;
	uint16_t len;

	if (!latest(id, &at, &len) || offset >= len) {
		return false;
	}
	flash[at + offset] ^= 0x01;
	return true;
}

void store_ram_save(struct store_ram_image *img)
{
	memcpy(img->flash, flash, sizeof(flash));
	img->head = head;
}

void store_ram_load(const struct store_ram_image *img)
{
	memcpy(flash, img->flash, sizeof(flash));
	head = img->head;
	budget = -1;
	cut = false;
}
