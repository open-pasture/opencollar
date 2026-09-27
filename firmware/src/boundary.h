/*
 * Bench boundary, for trying the fence and cues without a server.
 *
 * Only with CONFIG_OPENCOLLAR_BENCH_BOUNDARY=y (default n). Put the boundary
 * in boundary_local.h (gitignored, so farm and home locations stay out of the
 * public repo):
 *
 *   static const struct geo_point boundary_vertices[] = {
 *           {36.16270, -86.78160}, // {lat, lon}
 *           ...
 *   };
 *
 * It is loaded as version 0, in RAM only, when no boundary is in force, so
 * any boundary from the server (version 1 and up) replaces it. A collar
 * built without this option never invents a fence.
 */
#ifndef OPENCOLLAR_BOUNDARY_H
#define OPENCOLLAR_BOUNDARY_H

#ifdef CONFIG_OPENCOLLAR_BENCH_BOUNDARY

#include "geofence.h"

#if __has_include("boundary_local.h")
#include "boundary_local.h"
#else
#error "CONFIG_OPENCOLLAR_BENCH_BOUNDARY needs src/boundary_local.h (see boundary.h)"
#endif

#endif

#endif
