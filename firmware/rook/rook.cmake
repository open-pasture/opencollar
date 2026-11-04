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
    ${ROOK_DIR}/src/rook_battery_math.c
    ${ROOK_DIR}/src/rook_battery_max17260.c
  )
endif()
