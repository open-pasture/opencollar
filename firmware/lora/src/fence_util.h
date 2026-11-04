#ifndef OPENCOLLAR_FENCE_UTIL_H
#define OPENCOLLAR_FENCE_UTIL_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

static inline void oc_fh_be16(uint8_t *p, uint16_t v)
{
	p[0] = (uint8_t)(v >> 8);
	p[1] = (uint8_t)v;
}

static inline void oc_fh_be32(uint8_t *p, uint32_t v)
{
	p[0] = (uint8_t)(v >> 24);
	p[1] = (uint8_t)(v >> 16);
	p[2] = (uint8_t)(v >> 8);
	p[3] = (uint8_t)v;
}

static inline uint16_t oc_fh_rd16(const uint8_t *p)
{
	return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}

static inline uint32_t oc_fh_rd32(const uint8_t *p)
{
	return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) |
	       (uint32_t)p[3];
}

static inline int oc_fh_farm_eq(const uint8_t *a, const uint8_t *b)
{
	return memcmp(a, b, 8) == 0;
}

#endif
