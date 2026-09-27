/*
 * store.h on Zephyr NVS, on the `storage` partition (64 KB at 0xF0000, see
 * the board overlay). NVS writes the data, then its allocation table entry,
 * so an entry counts only once it is complete: a power cut leaves the old
 * value or the new one.
 */
#include <errno.h>
#include <zephyr/device.h>
#include <zephyr/drivers/flash.h>
#include <zephyr/kvss/nvs.h>
#include <zephyr/storage/flash_map.h>

#include "store.h"

static struct nvs_fs fs;
static bool mounted;

int store_init(void)
{
	struct flash_pages_info info;
	int err;

	fs.flash_device = PARTITION_DEVICE(storage_partition);
	if (!device_is_ready(fs.flash_device)) {
		return -ENODEV;
	}
	fs.offset = PARTITION_OFFSET(storage_partition);
	err = flash_get_page_info_by_offs(fs.flash_device, fs.offset, &info);
	if (err) {
		return err;
	}
	fs.sector_size = (uint16_t)info.size;
	fs.sector_count = (uint16_t)(PARTITION_SIZE(storage_partition) / info.size);
	err = nvs_mount(&fs);
	mounted = err == 0;
	return err;
}

int store_read(uint16_t id, void *buf, size_t cap)
{
	ssize_t n;

	if (!mounted) {
		return -ENODEV;
	}
	n = nvs_read(&fs, id, buf, cap);
	return (int)n;
}

int store_write(uint16_t id, const void *buf, size_t len)
{
	ssize_t n;

	if (!mounted) {
		return -ENODEV;
	}
	if (len == 0) {
		return -EINVAL;
	}
	n = nvs_write(&fs, id, buf, len);
	/* 0: identical data already stored; len: written */
	return n < 0 ? (int)n : 0;
}

int store_delete(uint16_t id)
{
	if (!mounted) {
		return -ENODEV;
	}
	return nvs_delete(&fs, id);
}
