# SPDX-License-Identifier: Apache-2.0
cmake_minimum_required(VERSION 3.20.0)

get_filename_component(RADIO_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../.. ABSOLUTE)
get_filename_component(FW_ROOT ${RADIO_ROOT}/.. ABSOLUTE)
list(APPEND SHIELD_ROOT ${RADIO_ROOT})
list(APPEND BOARD_ROOT ${FW_ROOT})

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(opencollar_radio_pingpong)

zephyr_include_directories(
  ${RADIO_ROOT}/include
  ${FW_ROOT}/lora/include
)

target_sources(app PRIVATE
  src/main.c
  ${RADIO_ROOT}/src/airtime.c
  ${RADIO_ROOT}/src/duty.c
  ${RADIO_ROOT}/src/backoff.c
  ${RADIO_ROOT}/src/sched.c
  ${RADIO_ROOT}/src/oc_radio.c
  ${RADIO_ROOT}/src/zephyr/oc_radio_zephyr.c
)
