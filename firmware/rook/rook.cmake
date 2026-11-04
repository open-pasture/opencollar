# SPDX-License-Identifier: Apache-2.0
# Included from firmware/CMakeLists.txt. Sources only with CONFIG_ROOK_LTE.
if(CONFIG_ROOK_LTE)
  set(ROOK_DIR ${CMAKE_CURRENT_LIST_DIR})
  target_include_directories(app PRIVATE ${ROOK_DIR}/src ${ROOK_DIR}/../src)
  target_sources(app PRIVATE
    ${ROOK_DIR}/src/rook_lte.c
    ${ROOK_DIR}/src/rook_queue.c
    ${ROOK_DIR}/src/rook_backoff.c
    ${ROOK_DIR}/src/rook_report.c
    ${ROOK_DIR}/src/rook_http.c
    ${ROOK_DIR}/src/rook_fence.c
    ${ROOK_DIR}/src/rook_state.c
    ${ROOK_DIR}/src/rook_ca.c
    ${ROOK_DIR}/src/rook_battery_math.c
    ${ROOK_DIR}/src/rook_battery_max17260.c
  )
  if(NOT "${CONFIG_ROOK_LTE_CA_PEM}" STREQUAL "")
    set(ROOK_CA_PATH ${ROOK_DIR}/../${CONFIG_ROOK_LTE_CA_PEM})
    if(NOT EXISTS ${ROOK_CA_PATH})
      message(FATAL_ERROR "CONFIG_ROOK_LTE_CA_PEM: ${ROOK_CA_PATH} not found")
    endif()
    generate_inc_file_for_target(app ${ROOK_CA_PATH}
      ${ZEPHYR_BINARY_DIR}/include/generated/rook_ca.pem.inc)
    target_compile_definitions(app PRIVATE ROOK_CA_EMBEDDED)
  endif()
endif()
