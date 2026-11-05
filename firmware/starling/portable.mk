# SPDX-License-Identifier: Apache-2.0
# Shared portable sources still living under firmware/src (no move yet).
# Include from a Makefile with STARLING_ROOT and SRC_ROOT set.

CORE_PORTABLE_SRCS = \
	$(SRC_ROOT)/protocol.c \
	$(SRC_ROOT)/shape.c \
	$(SRC_ROOT)/geofence.c \
	$(SRC_ROOT)/cue.c \
	$(SRC_ROOT)/command.c \
	$(SRC_ROOT)/slots.c \
	$(SRC_ROOT)/acks.c \
	$(SRC_ROOT)/config.c \
	$(SRC_ROOT)/provision.c

CORE_PORTABLE_HDRS = \
	$(SRC_ROOT)/protocol.h \
	$(SRC_ROOT)/shape.h \
	$(SRC_ROOT)/geofence.h \
	$(SRC_ROOT)/cue.h \
	$(SRC_ROOT)/command.h \
	$(SRC_ROOT)/slots.h \
	$(SRC_ROOT)/acks.h \
	$(SRC_ROOT)/config.h \
	$(SRC_ROOT)/provision.h \
	$(SRC_ROOT)/store.h \
	$(STARLING_ROOT)/../core/welfare.h
