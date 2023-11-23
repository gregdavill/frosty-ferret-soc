#
# This file is part of LiteSPI
#
# Copyright (c) 2020 Antmicro <www.antmicro.com>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *

from litex.gen.genlib.misc import WaitTimer

from litex.soc.interconnect import wishbone, stream
from litex.gen.common import reverse_bytes
from litex.soc.interconnect.csr import *

from hyperbus.common import *
from migen.genlib.cdc import MultiReg

class HyperBusMMAP(Module, AutoCSR):
    """Memory-mapped HyperBus Flash controller.

    The ``HyperBusMMAP`` class provides a Wishbone slave that must be connected to a HyperBus PHY.

    It supports sequential accesses so that command and address is only sent when necessary.

    Parameters
    ----------
    endianness : string
        If endianness is set to ``little`` then byte order of each 32-bit word coming from flash will be reversed.

    Attributes
    ----------
    source : Endpoint(spi_core2phy_layout), out
        PHY control interface.

    sink : Endpoint(spi_phy2core_layout), in
        PHY data interface.

    bus : Interface(), out
        Wishbone interface for memory-mapped flash access.

    cs : Signal(), out
        CS signal for the flash chip, should be connected to cs signal of the PHY.

    dummy_bits : CSRStorage
        Register which hold a number of dummy bits to send during transmission.
    """
    def __init__(self, endianness="big"):
        self.source = source = stream.Endpoint(spi_core2phy_layout)
        self.sink   = sink   = stream.Endpoint(spi_phy2core_layout)
        self.bus    = bus    = wishbone.Interface()
        self.cs     = cs     = Signal()

        # Burst Control.
        burst_cs      = Signal()
        burst_adr     = Signal(len(bus.adr), reset_less=True)
        burst_timeout = WaitTimer(1024) # TODO Fix this
        self.submodules += burst_timeout

        cmd_bits  = 8
        data_bits = 32

        self._default_dummy_bits = 0

        self._spi_dummy_bits = spi_dummy_bits = Signal(8)

        self.dummy_bits = dummy_bits = CSRStorage(8, reset=self._default_dummy_bits)
        self.comb += spi_dummy_bits.eq(dummy_bits.storage)

        addr = Signal(24)
        ca_bits = Signal(48)
        self.comb += [
            ca_bits[47].eq(~bus.we), # read = 1 / write = 0
            ca_bits[46].eq(0), # Memory Space
            ca_bits[45].eq(1), # Linear bursts
            ca_bits[16:44].eq(Cat(Constant(0, 7), addr[2:24])), # Upper column address
            ca_bits[3:15].eq(0), # Reserved
            ca_bits[0:2].eq(Cat(0b0, addr[0:1])), # Lower column address
        ]

        latency_cnt = Signal(5)
            

        dummy = Signal(data_bits, reset=0xdead)

        # FSM.
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act("IDLE",
            # Keep CS active after Burst for Timeout.
            burst_timeout.wait.eq(1),
            NextValue(burst_cs, burst_cs & ~burst_timeout.done),
            cs.eq(burst_cs),
            # On Bus Read access...
            If(bus.cyc & bus.stb & ~bus.we,
                # If CS is still active and Bus address matches previous Burst address:
                # Just continue the current Burst.
                If(burst_cs & (bus.adr == burst_adr),
                    NextState("WAIT"),
                    NextValue(latency_cnt, 2),
                # Otherwise initialize a new Burst.
                ).Else(
                    cs.eq(0),
                    NextState("BURST-CMD")
                )
            )
        )


        # TODO handle writes
        # TODO handle variable latency
        # TODO handle configurable latency

        fsm.act("BURST-CMD",
            cs.eq(1),
            source.valid.eq(1),
            addr.eq(bus.adr),
            source.data.eq(ca_bits[32:48]),
            source.len.eq(16),
            source.width.eq(8),
            source.mask.eq(0xFF),
            NextValue(burst_adr, bus.adr),
            If(source.ready,
                NextState("BURST-ADDR"),
            )
        )

        fsm.act("BURST-ADDR",
            cs.eq(1),
            source.valid.eq(1),
            addr.eq(bus.adr),
            source.data.eq(ca_bits[0:32]),
            source.len.eq(32),
            source.width.eq(8),
            source.mask.eq(0xFF),
            NextValue(burst_cs, 1),
            NextValue(burst_adr, bus.adr),
            NextValue(latency_cnt, 12),
            If(source.ready,
                NextState("DUMMY"),
            )
        )

        fsm.act("DUMMY",
            cs.eq(1),
            source.valid.eq(1),
            source.width.eq(8),
            source.mask.eq(0),
            source.len.eq(16),
            If(source.ready,
                NextValue(latency_cnt, latency_cnt - 1),
                If(latency_cnt == 0,
                    NextValue(latency_cnt, 2),
                    NextState("WAIT"),
                )
            )
        )

        fsm.act("WAIT",
            cs.eq(1),
            NextValue(latency_cnt, latency_cnt - 1),
            If(latency_cnt == 0,
                NextState("BURST-DAT"),
            )
        )

        fsm.act("BURST-DAT",
            cs.eq(1),
            sink.ready.eq(1),
            bus.dat_r.eq({"big": sink.data, "little": reverse_bytes(sink.data)}[endianness]),

            bus.ack.eq(1),
            NextValue(burst_adr, burst_adr + 1),
            NextState("IDLE"),
        )
