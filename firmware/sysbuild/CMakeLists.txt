# Sysbuild entry point (Zephyr's template) plus one step: build/merged.hex,
# the single flashable image = MCUboot (0x0) + signed TF-M/app (0x10000).
# Sysbuild's own SB_CONFIG_MERGED_HEX_FILES makes one file per board target,
# which splits MCUboot (secure target) from the app (/ns target).
find_package(Sysbuild REQUIRED HINTS $ENV{ZEPHYR_BASE})

project(sysbuild LANGUAGES)

if(SB_CONFIG_BOOTLOADER_MCUBOOT)
  set(mcuboot_hex ${CMAKE_BINARY_DIR}/mcuboot/zephyr/zephyr.hex)
  set(app_hex ${CMAKE_BINARY_DIR}/${DEFAULT_IMAGE}/zephyr/zephyr.signed.hex)
  set(merged_hex ${CMAKE_BINARY_DIR}/merged.hex)
  add_custom_target(opencollar_merged_hex ALL
    COMMAND ${PYTHON_EXECUTABLE} ${ZEPHYR_BASE}/scripts/build/mergehex.py
            --overlap error -o ${merged_hex} ${mcuboot_hex} ${app_hex}
    BYPRODUCTS ${merged_hex}
    COMMENT "Generating merged.hex (MCUboot + signed TF-M/app)"
  )
  add_dependencies(opencollar_merged_hex mcuboot ${DEFAULT_IMAGE})
endif()
