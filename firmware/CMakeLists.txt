cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(opencollar)

target_sources(app PRIVATE
  src/main.c
  src/geofence.c
  src/cue.c
  src/buzzer.c
)
