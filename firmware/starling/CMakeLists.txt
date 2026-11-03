# SPDX-License-Identifier: Apache-2.0
# Starling app for nRF52840 (Zephyr / NCS). Follows firmware/ west conventions.
cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(starling)

set(STARLING_DIR ${CMAKE_CURRENT_SOURCE_DIR})
set(FW_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/..)

target_sources(app PRIVATE
  src/main.c
  src/app.c
  src/fence_store.c
  src/gossip.c
  src/power.c
  src/gnss_fake.c
  src/gnss_ubx.c
  stubs/lora/fence_gossip.c
  stubs/radio/radio_hal.c
  # Shared portable core (still under firmware/src until op-firmware moves it)
  ${FW_ROOT}/src/geofence.c
  ${FW_ROOT}/src/cue.c
  ${FW_ROOT}/src/protocol.c
  ${FW_ROOT}/src/shape.c
  ${FW_ROOT}/src/store_nvs.c
  ${FW_ROOT}/third_party/monocypher/monocypher.c
  ${FW_ROOT}/third_party/monocypher/monocypher-ed25519.c
)

target_include_directories(app PRIVATE
  src
  ${FW_ROOT}/core
  ${FW_ROOT}/src
  ${FW_ROOT}/third_party/monocypher
  stubs/lora
  stubs/radio
)

target_compile_options(app PRIVATE -ffp-contract=off)
