# Portable fence-gossip library + host tests.
# Run: make -C firmware/lora test

CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O1 -g
CFLAGS += -D_POSIX_C_SOURCE=200809L
ROOT := $(abspath ../..)
LORA := $(abspath .)
SIM := $(abspath ../sim)
MONO := $(abspath ../third_party/monocypher)

INCLUDES := -I$(LORA)/include -I$(LORA)/src -I$(SIM)/include -I$(MONO)

LIB_SRC := \
	src/fence_hash.c \
	src/fence_manifest.c \
	src/fence_wire.c \
	src/fence_node.c \
	src/fence_build.c \
	src/fence_store_ram.c

SIM_SRC := \
	$(SIM)/src/sim_radio.c

MONO_SRC := \
	$(MONO)/monocypher.c \
	$(MONO)/monocypher-ed25519.c

BUILD := build
LIB_OBJ := $(LIB_SRC:src/%.c=$(BUILD)/%.o)
SIM_OBJ := $(BUILD)/sim_radio.o
MONO_OBJ := $(BUILD)/monocypher.o $(BUILD)/monocypher-ed25519.o

.PHONY: all test clean vectors loss report

all: test

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/%.o: src/%.c | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDES) -c -o $@ $<

$(BUILD)/sim_radio.o: $(SIM)/src/sim_radio.c | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDES) -c -o $@ $<

$(BUILD)/monocypher.o: $(MONO)/monocypher.c | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDES) -c -o $@ $<

$(BUILD)/monocypher-ed25519.o: $(MONO)/monocypher-ed25519.c | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDES) -c -o $@ $<

TESTS := test_vectors test_onehop test_chain test_security test_persist test_pilot test_maxfrag

$(BUILD)/test_vectors: tests/test_vectors.c $(LIB_OBJ) $(SIM_OBJ) $(MONO_OBJ)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $^

$(BUILD)/test_onehop: tests/test_onehop.c $(LIB_OBJ) $(SIM_OBJ) $(MONO_OBJ)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $^

$(BUILD)/test_chain: tests/test_chain.c $(LIB_OBJ) $(SIM_OBJ) $(MONO_OBJ)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $^

$(BUILD)/test_security: tests/test_security.c $(LIB_OBJ) $(SIM_OBJ) $(MONO_OBJ)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $^

$(BUILD)/test_persist: tests/test_persist.c $(LIB_OBJ) $(SIM_OBJ) $(MONO_OBJ)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $^

$(BUILD)/test_pilot: tests/test_pilot.c $(LIB_OBJ) $(SIM_OBJ) $(MONO_OBJ)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $^

$(BUILD)/test_maxfrag: tests/test_maxfrag.c $(LIB_OBJ) $(SIM_OBJ) $(MONO_OBJ)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $^

test: $(TESTS:%=$(BUILD)/%)
	@for t in $(TESTS); do echo "== $$t =="; $(BUILD)/$$t || exit 1; done

# Convenience: run the 30% loss suite and print the summary line.
loss: $(BUILD)/test_onehop
	$(BUILD)/test_onehop --loss30

clean:
	rm -rf $(BUILD)

# Stub: Zephyr native_sim target left for later (see RUNBOOK.md).
native_sim:
	@echo "native_sim: stub only — host sim in firmware/sim covers milestone tests."
