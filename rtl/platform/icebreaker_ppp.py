#
# This file is part of frosty-ferret-soc
#
# Copyright (c) 2023 Greg Davill <greg.davill@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

# OSHW ECP5 development board: https://github.com/gregdavill/advent-calendar-of-circuits-2020/tree/main/icebreaker%2B%2B-ram

from migen import *

from litex.build.generic_platform import *
from litex.build.lattice import LatticeECP5Platform
from litex.build.lattice.programmer import EcpprogProgrammer
from litex.soc.interconnect.csr import *

from migen.genlib.resetsync import AsyncResetSynchronizer

# IOs ----------------------------------------------------------------------------------------------

_io = [
    # Clk
    ("clk12", 0, Pins("L16"),  IOStandard("LVCMOS33")),
    
    # Buttons / Rst
    ("rst_n", 0, Pins("N16"), IOStandard("LVCMOS33")),

    # Leds
    ("user_led", 0, Pins("M16"), IOStandard("LVCMOS33")), # Red
    ("user_led", 1, Pins("M15"), IOStandard("LVCMOS33")), # Green
    # ("user_led", 2, Pins("A14"), IOStandard("LVCMOS33")), # Green
    # ("user_led", 3, Pins("B14"), IOStandard("LVCMOS33")), # Green
    # ("user_led", 4, Pins("A15"), IOStandard("LVCMOS33")), # Green
    ("rgb_led", 0,
        Subsignal("r", Pins("A14"), IOStandard("LVCMOS33")),
        Subsignal("g", Pins("B14"), IOStandard("LVCMOS33")),
        Subsignal("b", Pins("A15"), IOStandard("LVCMOS33")),
    ),

    # SPIFlash
    ("spiflash4x", 0,
        Subsignal("cs_n", Pins("N8")),
        #Subsignal("clk",  Pins("U3")),
        Subsignal("dq",   Pins("T8 T7 M7 N7")),
        IOStandard("LVCMOS33")
    ),
]

# Connectors ---------------------------------------------------------------------------------------

_connectors = [
]

# CRG ----------------------------------------------------------------------------------------------

class CRG(Module, AutoCSR):
    def __init__(self, platform, sys_clk_freq):
        reset_combo = Signal()

        self.clock_domains.cd_sys   = ClockDomain()
        clk_in = platform.request("clk12")
        self.comb += [
            self.cd_sys.clk.eq(clk_in)
        ]

        self.comb += reset_combo.eq(0)

        self.specials += [
            AsyncResetSynchronizer(self.cd_sys, reset_combo),
        ]

# Platform -----------------------------------------------------------------------------------------

class Platform(LatticeECP5Platform):
    default_clk_name   = "clk48"
    default_clk_period = 1e9/48e6
    crg = CRG

    def __init__(self, device="12F", toolchain="trellis", **kwargs):
        assert device in ["12F", "25F", "45F", "85F"]
        LatticeECP5Platform.__init__(self, f"LFE5U-{device}-8MG256C", _io, _connectors, toolchain=toolchain, **kwargs)
    
    def create_programmer(self):
        return EcpprogProgrammer()

    def do_finalize(self, fragment):
        LatticeECP5Platform.do_finalize(self, fragment)
        self.add_period_constraint(self.lookup_request("clk48", loose=True), 1e9/48e6)
