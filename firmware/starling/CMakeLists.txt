# SPDX-License-Identifier: Apache-2.0
cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(starling)

set(STARLING_DIR ${CMAKE_CURRENT_SOURCE_DIR})
set(FW_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/..)
set(LORA_DIR ${FW_ROOT}/lora)

target_sources(app PRIVATE
  src/main.c
  src/app.c
  src/fence_store.c
  src/gossip.c
  src/power.c
  src/gnss_fake.c
  src/gnss_ubx.c
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
)

if(EXISTS ${LORA_DIR}/include/opencollar/fence_node.h)
  message(STATUS "Starling: linking firmware/lora (oc_fh_*)")
  target_include_directories(app PRIVATE ${LORA_DIR}/include)
  target_sources(app PRIVATE
    src/oc_fh_store_nvs.c
    ${LORA_DIR}/src/fence_node.c
    ${LORA_DIR}/src/fence_manifest.c
    ${LORA_DIR}/src/fence_wire.c
    ${LORA_DIR}/src/fence_hash.c
  )
  target_compile_definitions(app PRIVATE STARLING_HAS_LORA=1)
else()
  message(STATUS "Starling: firmware/lora absent — pending_opencollar freshness shim")
  # DELETE pending_opencollar/ when PR #6 merges.
  target_include_directories(app PRIVATE ${STARLING_DIR}/pending_opencollar)
endif()

target_compile_options(app PRIVATE -ffp-contract=off)
