/*
 * Persistence by numeric id (protocol v1 §3.7).
 *
 * The firmware backend is Zephyr NVS on the `storage` partition
 * (store_nvs.c); host tests use tests/host/store_ram.c, which can cut power
 * at any byte. A write is atomic: after a power cut the id holds the old
 * value or the new one (NVS counts an entry once its allocation table entry
 * is written). A NOR backend (ZMS or littlefs) can replace NVS behind these
 * four functions without touching the code that uses them.
 */
#ifndef OPENCOLLAR_STORE_H
#define OPENCOLLAR_STORE_H

#include <stddef.h>
#include <stdint.h>

#define STORE_ID_PROVISION 1   /* The provisioning payload (§3.9) */
#define STORE_ID_ACKS 2        /* Acks not yet delivered */
#define STORE_ID_CONFIG 3      /* The applied config command (§3.4) */
#define STORE_ID_SLOT_BASE 0x100 /* Slot records: 0x100 + i */

/* Mount the store. 0 or a negative errno. */
int store_init(void);

/* Read an entry into buf. Returns the entry's size in bytes (more than cap
 * means it didn't fit and buf holds only the start), -ENOENT when there is
 * none, or another negative errno. */
int store_read(uint16_t id, void *buf, size_t cap);

/* Write an entry (len > 0). 0 or a negative errno. */
int store_write(uint16_t id, const void *buf, size_t len);

/* Delete an entry. Deleting one that doesn't exist is not an error. */
int store_delete(uint16_t id);

#endif
