"""Toolchain check: builds a tiny circuit (LED + resistor on a header) and writes a KiCad netlist."""
from skidl import Part, Net, generate_netlist, set_default_tool, KICAD9

set_default_tool(KICAD9)  # KiCad 10 reads the KiCad 9 library format

vcc, gnd = Net("3V3"), Net("GND")
hdr = Part("Connector_Generic", "Conn_01x02", footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
r = Part("Device", "R", value="1k", footprint="Resistor_SMD:R_0603_1608Metric")
led = Part("Device", "LED", footprint="LED_SMD:LED_0603_1608Metric")
vcc += hdr[1], r[1]
r[2] & led["A"]
led["K"] += gnd
gnd += hdr[2]
generate_netlist(file_="build/smoke.net")
print("ok")
