"""OpenCollar carrier board rev A2: the schematic, as code.

Spec: SPEC.md (rev A2). Every block below cites the datasheet section it follows;
the [refs] are the ones in SPEC.md's source table. Breakout boards (SparkFun,
Adafruit) are used only for their mating pinout, never as a circuit source.

    source env.sh && uv run python schematic.py     # writes build/carrier.net + ERC

Part fields: LCSC = JLCPCB/LCSC part number, DNP = "1" for parts not fitted.
"""
import builtins

from skidl import (ERC, KICAD9, POWER, SKIDL, TEMPLATE, Net, Part, Pin,
                   generate_netlist, set_default_tool)
from skidl.pin import pin_types as T

set_default_tool(KICAD9)  # KiCad 10 reads the KiCad 9 library format
NC = builtins.NC          # SKiDL's no-connect net

R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
SOCKET = "Connector_PinSocket_2.54mm:PinSocket_1x{n:02d}_P2.54mm_Vertical_SMD_Pin1Left"
PH_H = "Connector_JST:JST_PH_S{n}B-PH-SM4-TB_1x{n:02d}-1MP_P2.00mm_Horizontal"
SH_H = "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal"
SH3_H = "Connector_JST:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal"
TP_FP = "TestPoint:TestPoint_Pad_D1.0mm"

# LCSC numbers, from JLCPCB's parts search on 2026-09-26 (SPEC.md section 10).
# Keys are MPNs, or R_/C_<value>_<package> for passives.
LCSC = {
    "BQ24074RGTR": "C54313", "TCA4307DGKR": "C880333", "TPS2553DBVR": "C55266",
    "USBLC6-2SC6": "C7519", "B5819W": "C8598",
    "R_887_1608Metric": "C93619", "R_3.24k_1608Metric": "C22994", "R_71.5k_1608Metric": "C23103",
    "R_100k_1608Metric": "C25803", "R_10k_1608Metric": "C25804", "R_4.7k_1608Metric": "C23162",
    "R_1M_1608Metric": "C22935", "R_200k_1608Metric": "C25811", "R_1k_1608Metric": "C21190",
    "C_10u/25V_2012Metric": "C15850", "C_100n_1608Metric": "C14663",
    "C_10n_1608Metric": "C57112", "C_1u_1608Metric": "C15849",
}
CONN_LCSC = {   # by footprint
    "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal": ("C295747", "S2B-PH-SM4-TB(LF)(SN)"),
    "JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal": ("C265101", "S3B-PH-SM4-TB(LF)(SN)"),
    "JST_PH_S8B-PH-SM4-TB_1x08-1MP_P2.00mm_Horizontal": ("C265121", "S8B-PH-SM4-TB(LF)(SN)"),
    "JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal": ("C160404", "SM04B-SRSS-TB(LF)(SN)"),
    "JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal": ("C160403", "SM03B-SRSS-TB(LF)(SN)"),
    # hanxia 8.5 mm SMD sockets; check their pad stagger against KiCad's Pin1Left (SPEC.md 11)
    "PinSocket_1x10_P2.54mm_Vertical_SMD_Pin1Left": ("C46635846", "HX PM2.54-1x10P TP H8.5-YQ"),
    "PinSocket_1x09_P2.54mm_Vertical_SMD_Pin1Left": ("C46635845", "HX PM2.54-1x9P TP H8.5-YQ"),
    "PinSocket_1x08_P2.54mm_Vertical_SMD_Pin1Left": ("C46635844", "HX PM2.54-1x8P TP H8.5-YQ"),
    "PinSocket_1x04_P2.54mm_Vertical_SMD_Pin1Left": ("C46635840", "HX PM2.54-1x4P TP H8.5-YQ"),
}


BLOCK = ["top"]
_count = {}


def P(*args, ref=None, **kw):
    """Part() that records its block (layout.py places by block) and gets a stable tag."""
    b = BLOCK[0]
    _count[b] = _count.get(b, 0) + 1
    tmpl = kw.pop("template", None)
    part = tmpl(tag=f"{b}.{_count[b]}", **kw) if tmpl else Part(*args, tag=f"{b}.{_count[b]}", **kw)
    part.fields["block"] = b
    if ref:
        part.ref = ref
    return part


def block(fn):
    """Decorator: parts created inside fn belong to block fn.__name__."""
    def run(*a, **k):
        BLOCK[0] = fn.__name__
        return fn(*a, **k)
    run.__doc__, run.__name__ = fn.__doc__, fn.__name__
    return run


def lcsc(part, key):
    if key in LCSC:
        part.fields["LCSC"] = LCSC[key]
    part.fields["MPN"] = key
    return part


def R(value, fp=R0603, dnp=False):
    r = P("Device", "R", value=value, footprint=fp)
    if dnp:
        r.fields["DNP"] = "1"
    return lcsc(r, f"R_{value}_{fp.split('_')[-1]}")


def C(value, fp=C0603):
    return lcsc(P("Device", "C", value=value, footprint=fp), f"C_{value}_{fp.split('_')[-1]}")


def conn(n, fp, value, ref=None):
    c = P("Connector_Generic", f"Conn_01x{n:02d}", footprint=fp, value=value, ref=ref)
    if fp.split(":")[1] in CONN_LCSC:
        c.fields["LCSC"], c.fields["MPN"] = CONN_LCSC[fp.split(":")[1]]
    return c


# ------------------------------------------------------------------ nets

def N(name):
    """The net called `name`, created on first use, so blocks share nets by name."""
    return Net.get(name) or Net(name)



GND = N("GND")
V3V3 = N("3V3")          # the Connect Kit's VIO (TPS63901) [TPS]
BAT = N("BAT")           # the pack: over the harness, or J_BAT on the bench
CHG_IN = N("CHG_IN")     # bq24074 IN, after the panel diodes
CHG_OUT = N("CHG_OUT")   # bq24074 OUT -> Kit J2
EXT_3V3 = N("EXT_3V3")   # switched, current-limited 3.3 V for everything outside the box
for n in (GND, V3V3, BAT, CHG_IN, CHG_OUT, EXT_3V3):
    n.drive = POWER

SDA, SCL = N("I2C_SDA"), N("I2C_SCL")          # main bus, nRF TWIM2
EXT_SDA, EXT_SCL = N("EXT_SDA"), N("EXT_SCL")  # behind the TCA4307
TS = N("TS")


# ------------------------------------------------------------------ blocks

@block
def connect_kit():
    """Makerdiary nRF9151 Connect Kit rev A [MD front diagram, dimension drawing]. Rows
    17.78 mm apart; pin 1 (VBUS) and pin 40 (VIO) at the USB end. Left row: J1 = Kit
    1-10, J2 = 11-20. Right row: J3 = Kit 40-31, J4 = 30-21. Every socket numbers from
    the USB end. Pin use: SPEC.md section 2."""
    kit = {
        1: "KIT_VBUS", 2: "KIT_VSYS", 3: GND, 4: "KIT_EN",
        5: "CHG_CE", 6: "EXT_INT", 7: "EXT_EN", 8: "EXT_READY", 9: "EXT_FAULT",
        10: NC, 11: NC, 12: NC, 13: NC, 14: NC,           # spare P0.04-P0.00
        15: SCL, 16: SDA, 17: "IMU_INT1", 18: "IMU_INT2", 19: "GNSS_EXTINT", 20: "GNSS_RESET_N",
        21: "VBAT_SENSE", 22: "ISET_SENSE", 23: "VIN_SENSE",
        24: NC, 25: NC, 26: NC, 27: NC, 28: NC,           # spare AIN3-AIN7
        29: "CHG_STAT", 30: "GNSS_RXD", 31: "GNSS_TXD", 32: "GNSS_PPS", 33: "CHG_PGOOD",
        34: "UART_TX", 35: "UART_RX", 36: "SWDIO", 37: "SWCLK", 38: "RESET",
        39: GND, 40: V3V3,
    }
    # No 1x20 SMD socket is stocked, so each row is two 1x10s end to end (25.4 mm).
    socks = {"J1": (1, 1), "J2": (11, 1), "J3": (40, -1), "J4": (30, -1)}  # first Kit pin, step
    parts = {r: conn(10, SOCKET.format(n=10), f"Kit {a}-{a + 9 * d}", ref=r) for r, (a, d) in socks.items()}
    for ref, (first, step) in socks.items():
        for k in range(1, 11):
            net = kit[first + step * (k - 1)]
            parts[ref][k] += N(net) if isinstance(net, str) else net
    return kit


@block
def kit_battery_feed():
    """bq24074 OUT to the Kit's J2 battery input (MX1.25) through a 1.25 mm pigtail
    soldered into two plated holes. The header has no battery pin [MD back]. OUT is
    4.3-4.5 V with input [BQ] 8.5 VO(REG), inside J2's 3.6-4.65 V [MD]."""
    j = conn(2, "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "Kit J2 feed", ref="J5")
    j.fields["DNP"] = "1"  # plated holes; the pigtail's wires are soldered in
    j[1] += CHG_OUT
    j[2] += GND


@block
def charger():
    """bq24074 standalone, USB500 mode. All from [BQ] (SLUS810N):
    EN2 = 0 / EN1 = 1 -> 500 mA input limit with VIN-DPM, Table 7-2 and 8.5;
    ISET 887 R -> 1.0 A programmed (input-limited), eq. 2; ILIM 3.24 k must be
    fitted, Table 7-1; TMR 71.5 k -> 9.5 h fast / 57 min pre-charge, eq. 6-7;
    ITERM open -> 10 %, 9.3.5.2; TS to the pack NTC, 9.3.6; CE low = charge, Table 7-1;
    caps per Table 7-1; thermal pad to VSS with four 0.3 mm vias (layout.py), 12.1."""
    u = lcsc(P("Battery_Management", "BQ24074RGT", ref="U1",
               footprint="Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm"),
             "BQ24074RGTR")
    u["IN"] += CHG_IN
    u["OUT"] += CHG_OUT
    u["BAT"] += BAT
    u["VSS"] += GND
    u["EN2"] += GND
    r_en1 = R("10k")                     # EN1 high from OUT, so it charges without the Kit
    r_en1[1] += CHG_OUT
    r_en1[2] += u["EN1"]
    iset = N("ISET")
    u["ISET"] += iset
    R("887")[1, 2] += iset, GND
    R("3.24k")[1, 2] += u["ILIM"], GND
    R("71.5k")[1, 2] += u["TMR"], GND
    u["ITERM"] += NC
    u["TS"] += TS
    C("10n")[1, 2] += TS, GND            # filters pickup on the ~0.6 m NTC run
    R("10k", dnp=True)[1, 2] += TS, GND  # fit only to charge with no NTC: [BQ] 10.2.2.3
    ce = N("CHG_CE")
    u["~{CE}"] += ce
    R("100k")[1, 2] += ce, GND
    stat, pg = N("CHG_STAT"), N("CHG_PGOOD")
    u["~{CHG}"] += stat
    u["~{PGOOD}"] += pg
    R("100k")[1, 2] += stat, V3V3        # [BQ] 10.2.2.4
    R("100k")[1, 2] += pg, V3V3
    for net in (CHG_IN, CHG_OUT, BAT):   # [BQ] Table 7-1
        C("10u/25V", C0805)[1, 2] += net, GND


@block
def solar_inputs():
    """Two P124 panels on one 3-pin JST SH (1 panel A+, 2 GND, 3 panel B+), each through
    its own Schottky into IN, so a lit panel can't push current into a shaded one.
    P124: Vmp 6.0 V, Voc <= 7.28 V, Isc <= 0.23 A [P124]. SH is rated 1 A per contact;
    both panels together are <= 0.46 A on the GND pin."""
    j = conn(3, SH3_H, "Panels A/GND/B", ref="J6")
    j[2] += GND
    for name, pin, dref in (("A", 1, "D1"), ("B", 3, "D2")):
        sol = N(f"SOLAR_{name}")
        j[pin] += sol
        d = lcsc(P("Device", "D_Schottky", value="B5819W", footprint="Diode_SMD:D_SOD-123", ref=dref), "B5819W")
        d["A"] += sol
        d["K"] += CHG_IN


@block
def sensing():
    """nRF9151 SAADC inputs (AIN0-2). High-value dividers draw ~2 uA; the 100 nF
    holds the sample, with a 40 us acquisition time in firmware."""
    vb = N("VBAT_SENSE")
    R("1M")[1, 2] += BAT, vb
    R("1M")[1, 2] += vb, GND
    C("100n")[1, 2] += vb, GND
    vi = N("VIN_SENSE")                 # 8 V -> 1.33 V
    R("1M")[1, 2] += CHG_IN, vi
    R("200k")[1, 2] += vi, GND
    C("100n")[1, 2] += vi, GND
    R("100k")[1, 2] += N("ISET"), N("ISET_SENSE")   # V = ICHG/400 x RISET, [BQ] eq. 3


@block
def main_i2c():
    """Main bus (TWIM2, P0.30/P0.31): 4.7 k pull-ups to 3V3, plus a spare Qwiic
    socket inside the box (Qwiic order GND, 3V3, SDA, SCL)."""
    R("4.7k")[1, 2] += SDA, V3V3
    R("4.7k")[1, 2] += SCL, V3V3
    q = conn(4, SH_H, "Qwiic spare", ref="J7")
    q[1, 2, 3, 4] += GND, V3V3, SDA, SCL


@block
def gnss_sockets():
    """SparkFun MAX-M10S breakout (GPS-18037) on its 8-pin edge row and 4-pin I2C row
    [SF board file: mating pinout only]. EXTINT wakes from standby, RESET_N low >= 1 ms
    resets, TIMEPULSE shares SAFEBOOT_N so nothing may pull it low at boot [UBX] Table 10."""
    a = conn(8, SOCKET.format(n=8), "M10S J5", ref="J8")
    a[1, 2, 3, 4, 5, 6, 7, 8] += (GND, V3V3, N("GNSS_SAFEBOOT"), N("GNSS_TXD"),
                                  N("GNSS_RXD"), N("GNSS_PPS"),
                                  N("GNSS_EXTINT"), N("GNSS_RESET_N"))
    b = conn(4, SOCKET.format(n=4), "M10S J3", ref="J9")
    b[1, 2, 3, 4] += GND, V3V3, SDA, SCL


@block
def imu_socket():
    """Adafruit ISM330DHCX (4502) 9-pin row: VIN, 3Vo, GND, SCL, SDA, DO, CS, INT1, INT2
    [SF: LSM6DSOX board file, same outline; check the ISM330 silkscreen]. DO open ->
    address 0x6A; CS open (board pull-up) -> I2C mode."""
    j = conn(9, SOCKET.format(n=9), "ISM330", ref="J10")
    j[1, 2, 3, 4, 5, 6, 7, 8, 9] += (V3V3, NC, GND, SCL, SDA, NC, NC,
                                     N("IMU_INT1"), N("IMU_INT2"))


TCA4307 = Part(name="TCA4307", tool=SKIDL, dest=TEMPLATE, ref_prefix="U",
               footprint="Package_SO:VSSOP-8_3x3mm_P0.65mm", pins=[
                   Pin(num="1", name="EN", func=T.INPUT),
                   Pin(num="2", name="SCLOUT", func=T.BIDIR),
                   Pin(num="3", name="SCLIN", func=T.BIDIR),
                   Pin(num="4", name="GND", func=T.PWRIN),
                   Pin(num="5", name="READY", func=T.OPENCOLL),
                   Pin(num="6", name="SDAIN", func=T.BIDIR),
                   Pin(num="7", name="SDAOUT", func=T.BIDIR),
                   Pin(num="8", name="VCC", func=T.PWRIN)])   # [TCA] Figure 4-1, DGK package

TPS2553 = Part(name="TPS2553", tool=SKIDL, dest=TEMPLATE, ref_prefix="U",
               footprint="Package_TO_SOT_SMD:SOT-23-6", pins=[
                   Pin(num="1", name="IN", func=T.PWRIN),
                   Pin(num="2", name="GND", func=T.PWRIN),
                   Pin(num="3", name="EN", func=T.INPUT),
                   Pin(num="4", name="FAULT", func=T.OPENCOLL),
                   Pin(num="5", name="ILIM", func=T.PASSIVE),
                   Pin(num="6", name="OUT", func=T.PWROUT)])  # [TPS25] Pin Functions, DBV


@block
def external_bus():
    """Everything that leaves the box sits behind one switch, EXT_EN (P0.07, pulled low):
    - TCA4307 hot-swap buffer between the main bus (IN side) and EXT (OUT side). Pull-ups
      on both sides, 0.1 uF at VCC, READY 10 k to VCC [TCA] pin functions. Stuck-bus
      recovery after ~40 ms and 7 V-tolerant bus pins [TCA] p.1, 5.1.
    - TPS2553 current-limited switch 3V3 -> EXT_3V3. RILIM 100 k -> ~260 mA
      (IOS 520 mA at 49.9 k, 130 mA at 210 k) [TPS25] 7.5; 0.1 uF+ at IN [TPS25] pin table.
    EXT pull-ups go to EXT_3V3 so nothing outside is back-powered while it's off."""
    en = N("EXT_EN")
    R("100k")[1, 2] += en, GND
    b = lcsc(P(template=TCA4307, ref="U2"), "TCA4307DGKR")
    b["VCC"] += V3V3
    b["GND"] += GND
    b["EN"] += en
    b["SDAIN"] += SDA
    b["SCLIN"] += SCL
    b["SDAOUT"] += EXT_SDA
    b["SCLOUT"] += EXT_SCL
    b["READY"] += N("EXT_READY")
    R("10k")[1, 2] += N("EXT_READY"), V3V3
    C("100n")[1, 2] += V3V3, GND
    R("4.7k")[1, 2] += EXT_SDA, EXT_3V3
    R("4.7k")[1, 2] += EXT_SCL, EXT_3V3

    s = lcsc(P(template=TPS2553, ref="U3"), "TPS2553DBVR")
    s["IN"] += V3V3
    s["GND"] += GND
    s["EN"] += en
    s["OUT"] += EXT_3V3
    R("100k")[1, 2] += s["ILIM"], GND
    s["FAULT"] += N("EXT_FAULT")
    R("100k")[1, 2] += N("EXT_FAULT"), V3V3
    C("1u")[1, 2] += V3V3, GND
    C("1u")[1, 2] += EXT_3V3, GND


@block
def cue_ports():
    """Left and right ear-pod buzzers (SparkFun Qwiic Buzzer, 0x34 left, 0x5B right) on
    the EXT bus: Qwiic order GND, EXT_3V3, EXT_SDA, EXT_SCL. Left/right because cattle
    localise to ~30 deg (docs/COLLAR-FIRST-PRINCIPLES.md section 1)."""
    for side, ref in (("L", "J11"), ("R", "J12")):
        q = conn(4, SH_H, f"Cue {side}", ref=ref)
        q[1, 2, 3, 4] += GND, EXT_3V3, EXT_SDA, EXT_SCL


@block
def harness_port():
    """The one battery path: M8 8-pin strap harness to the battery module. On the bench,
    a PH8 pigtail brings the pack and its NTC to the same socket (no second battery
    connector, so two packs can never be connected at once). Harness (SPEC.md section 5; IEC 61076-2-104
    pin order, DIN 47100 colours): 1 SDA, 2 BAT+, 3 GND, 4 SCL, 5 NTC, 6 INT, 7 GND, 8 BAT+.
    Power doubled so one broken conductor doesn't drop the pack. INT gets 1 k in series
    and a 100 k pull-up to 3V3 before the nRF pin."""
    j = conn(8, PH_H.format(n=8), "Harness M8", ref="J13")
    int_raw = N("EXT_INT_RAW")
    j[1, 2, 3, 4, 5, 6, 7, 8] += EXT_SDA, BAT, GND, EXT_SCL, TS, int_raw, GND, BAT
    R("1k")[1, 2] += int_raw, N("EXT_INT")
    R("100k")[1, 2] += N("EXT_INT"), V3V3


@block
def esd():
    """USBLC6-2SC6 on every line that leaves the box (ST datasheet: I/O1 pins 1/6,
    I/O2 pins 3/4, VBUS 5 is the rail clamp, GND 2)."""
    fp = "Package_TO_SOT_SMD:SOT-23-6"
    a = lcsc(P("Power_Protection", "USBLC6-2SC6", footprint=fp, ref="U4"), "USBLC6-2SC6")
    a[1] += EXT_SDA; a[6] += EXT_SDA
    a[3] += EXT_SCL; a[4] += EXT_SCL
    a["VBUS"] += EXT_3V3
    a["GND"] += GND
    b = lcsc(P("Power_Protection", "USBLC6-2SC6", footprint=fp, ref="U5"), "USBLC6-2SC6")
    b[1] += TS; b[6] += TS
    b[3] += N("EXT_INT_RAW"); b[4] += N("EXT_INT_RAW")
    b["VBUS"] += BAT
    b["GND"] += GND


@block
def test_pads():
    """1.0 mm pads on the bottom for a pogo fixture (SPEC.md section 7). Placed on the
    bottom by layout.py; the value is the silkscreen label."""
    names = ["BAT", "CHG_OUT", "CHG_IN", "SOLAR_A", "SOLAR_B", "3V3", "EXT_3V3",
             "KIT_VBUS", "KIT_VSYS", "GND", "GND", "GND", "GND",
             "SWDIO", "SWCLK", "RESET", "UART_TX", "UART_RX", "KIT_EN",
             "I2C_SDA", "I2C_SCL", "EXT_SDA", "EXT_SCL", "EXT_EN", "EXT_INT",
             "TS", "ISET", "CHG_STAT", "CHG_PGOOD", "CHG_CE",
             "GNSS_SAFEBOOT", "GNSS_RESET_N", "GNSS_PPS"]
    for n in names:
        tp = P("Connector", "TestPoint", value=n, footprint=TP_FP)
        tp.fields["DNP"] = "1"   # bare pads, nothing to place
        tp[1] += N(n)


@block
def mechanical():
    """Holes [SF]. H1, H2: M3 board mounts under the Kit, between its socket rows.
    H3, H4: the MAX-M10S's two corner holes away from its 8-pin row; M3 male-female
    standoffs there hold the M10S and screw the carrier to the box posts (the two holes
    beside the 8-pin row sit under the SMD socket, which holds that edge). H5, H6: the
    ISM330's Ø2.5 holes with M2 standoffs. Positions in layout.py."""
    for i in range(1, 5):
        P("Mechanical", "MountingHole", footprint="MountingHole:MountingHole_3.2mm_M3", ref=f"H{i}")
    for i in (5, 6):
        P("Mechanical", "MountingHole", footprint="MountingHole:MountingHole_2.2mm_M2", ref=f"H{i}")


if __name__ == "__main__":
    connect_kit()
    kit_battery_feed()
    charger()
    solar_inputs()
    sensing()
    main_i2c()
    gnss_sockets()
    imu_socket()
    external_bus()
    cue_ports()
    harness_port()
    esd()
    test_pads()
    mechanical()
    ERC()
    generate_netlist(file_="build/carrier.net")
