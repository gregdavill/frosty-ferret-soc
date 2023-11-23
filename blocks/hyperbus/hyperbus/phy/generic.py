#
# This file is part of LiteSPI
#
# Copyright (c) 2020 Antmicro <www.antmicro.com>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from migen.genlib.cdc import MultiReg

from litex.gen.genlib.misc import WaitTimer

from hyperbus.common import *

from litex.soc.interconnect.csr import *

from litex.soc.integration.doc import AutoDoc

from hyperbus.phy.ddr import HyperBusDDRPHYCore

# HyperBus PHY --------------------------------------------------------------------------------------

class HyperBusPHY(Module, AutoCSR, AutoDoc):
    """HyperBus PHY instantiator

    The ``HyperBusPHY`` class instantiate generic PHY - ``HyperBusPHYCore`` that can be connected to the ``HyperBusCore``,
    handles optional clock domain wrapping for whole PHY and interfaces streams and CS signal from PHY logic.

    Parameters
    ----------
    pads : Object
        HyperBus pads description.

    Attributes
    ----------
    source : Endpoint(spi_phy2core_layout), out
        Data stream from ``HyperBusPHYCore``.

    sink : Endpoint(spi_core2phy_layout), in
        Control stream from ``HyperBusPHYCore``.

    cs : Signal(), in
        Flash CS signal from ``HyperBusPHYCore``.
    """

    def __init__(self, pads, cs_delay=10, extra_latency=0):

        self.phy = HyperBusDDRPHYCore(pads, cs_delay, extra_latency)

        self.source = self.phy.source
        self.sink   = self.phy.sink
        self.cs     = self.phy.cs

        # # #

        self.submodules.spiflash_phy = self.phy

    def get_csrs(self):
        return self.spiflash_phy.get_csrs()
