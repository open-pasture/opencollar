cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(opencollar)

target_sources(app PRIVATE
  src/main.c
  src/app.c
  src/acks.c
  src/buzzer.c
  src/command.c
  src/config.c
  src/console.c
  src/cue.c
  src/geofence.c
  src/protocol.c
  src/provision.c
  src/shape.c
  src/slots.c
  src/store_nvs.c
  third_party/monocypher/monocypher.c
  third_party/monocypher/monocypher-ed25519.c
)

target_include_directories(app PRIVATE third_party/monocypher)

# The shape rules are single precision in a fixed order of operations, to
# give the same answers as openpasture's op_geo::shape: no fused multiply-add.
target_compile_options(app PRIVATE -ffp-contract=off)
