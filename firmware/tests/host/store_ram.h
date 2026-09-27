/*
 * store.h in RAM for host tests, with power cuts.
 *
 * Entries are appended to a 64 KB log as [id][length][data][commit byte],
 * and an entry counts only once its commit byte is written, which is how NVS
 * treats an entry whose allocation table entry is written last. A power cut
 * after any number of bytes leaves an unfinished entry that the next mount
 * drops, so a key keeps its old value or gets the new one.
 */
#ifndef TEST_STORE_RAM_H
#define TEST_STORE_RAM_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define STORE_RAM_BYTES 65536

struct store_ram_image {
	uint8_t flash[STORE_RAM_BYTES];
	size_t head;
};

/* Erase everything, power on */
void store_ram_reset(void);
/* Cut the power after n more bytes are written (-1: never) */
void store_ram_cut_after(long n);
/* Whether the power is off */
bool store_ram_is_cut(void);
/* Power back on: mount again, dropping an unfinished entry */
void store_ram_reboot(void);
/* Bytes written since the last reset */
size_t store_ram_written(void);
/* Flip one bit in the data of id's live entry (a flash fault) */
bool store_ram_corrupt(uint16_t id, size_t offset);
void store_ram_save(struct store_ram_image *img);
void store_ram_load(const struct store_ram_image *img);

#endif
