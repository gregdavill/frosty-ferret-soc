#
# This file is part of frosty-ferret-soc
#
# Copyright (c) 2023 Greg Davill <greg.davill@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

# OSHW ECP5 development board: https://github.com/gregdavill/advent-calendar-of-circuits-2020/tree/main/icebreaker%2B%2B-ram

from migen import *

from litex.build.sim.platform import SimPlatform
from litex.build.generic_platform import Pins, IOStandard, Misc, Subsignal

from litex.build.generic_platform import *
from litex.soc.interconnect.csr import *

_io = [

    # LEDs
    ("user_led", 0, Pins(1)), # Red
    ("user_led", 1, Pins(1)), # Green

    # SPIFlash
    ("spiflash4x", 0,
        Subsignal("cs_n", Pins(1)),
        Subsignal("clk",  Pins(1)),
        Subsignal("dq",   Pins(4)),
    ),
    # Hyperbus
    ("hyperbus0", 0,
        Subsignal("reset_n", Pins(1)),
        Subsignal("cs_n", Pins(1)),
        Subsignal("clk_p",  Pins(1)),
        Subsignal("clk_n",  Pins(1)),
        Subsignal("dq",   Pins(8)),
        Subsignal("rwds",  Pins(1))
    ),
    ("serial", 0,
        Subsignal("tx", Pins(1)),
        Subsignal("rx", Pins(1)),
    ),

    ("clk", 0, Pins(1)),
    ("reset", 0, Pins(1)),
]

_connectors = [

]

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        clk = platform.request("clk")
        rst = platform.request("reset")


        
        self.clock_domains.cd_sys = ClockDomain()
        self.comb += self.cd_sys.clk.eq(clk)

        # Power on reset
        self.clock_domains.cd_por     = ClockDomain()
        por_count = Signal(7, reset=2**7-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(clk)
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        self.comb += [
            ResetSignal("sys").eq(rst | ~por_done),
            ResetSignal("por").eq(rst),
        ]

class Platform(SimPlatform):
    crg = _CRG

    def __init__(self, toolchain="icarus"):
        SimPlatform.__init__(self, "sim", _io, _connectors, toolchain="verilator")
        self.name="dut"
        
    def create_programmer(self):
        raise ValueError("programming is not supported")
