/*
 * V0 boundary, compiled in until boundary download over LTE exists.
 *
 * Put a real boundary in boundary_local.h (gitignored, so farm and home
 * locations stay out of the public repo). Without it, the example below is used.
 */
#ifndef OPENCOLLAR_BOUNDARY_H
#define OPENCOLLAR_BOUNDARY_H

#include "geofence.h"

#if __has_include("boundary_local.h")
#include "boundary_local.h"
#else
/* Example: ~100 m square in Nashville. Replace via boundary_local.h. */
#define BOUNDARY_VERSION 0
static const struct geo_point boundary_vertices[] = {
	{36.16270, -86.78160},
	{36.16270, -86.78049},
	{36.16360, -86.78049},
	{36.16360, -86.78160},
};
#endif

#endif
