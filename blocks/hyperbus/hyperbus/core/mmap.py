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
        burst_we      = Signal()
        burst_adr     = Signal(len(bus.adr), reset_less=True)
        burst_timeout = WaitTimer(5) # TODO Fix this
        self.submodules += burst_timeout

        cmd_bits  = 8
        data_bits = 32

        self._latency_cycles = CSRStorage(8, reset=6)
        _latency_cycles = self._latency_cycles.storage
        _extra_latency_flag = Signal()

        addr = Signal(24)
        ca_bits = Signal(48)
        self.comb += [
            ca_bits[47].eq(~bus.we), # read = 1 / write = 0
            ca_bits[46].eq(0), # Memory Space
            ca_bits[45].eq(1), # Linear bursts
            ca_bits[16:45].eq(addr[2:24]), # Upper column address
            ca_bits[3:16].eq(0), # Reserved
            ca_bits[0:3].eq(Cat(Constant(0, 1), addr[0:2])), # Lower column address
        ]

        latency_cnt = Signal(5)

        # FSM.
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act("IDLE",
            # Keep CS active after Burst for Timeout.
            burst_timeout.wait.eq(1),
            NextValue(burst_cs, burst_cs & ~burst_timeout.done),
            cs.eq(burst_cs),
            # On Bus Read access...
            If(bus.cyc & bus.stb,
                # If CS is still active and Bus address matches previous Burst address:
                # Just continue the current Burst.
                If(burst_cs & (bus.adr == burst_adr) & (burst_we == bus.we),
                    If(bus.we,
                        NextState("BURST-WR")
                    ).Else(       
                        NextValue(latency_cnt, 1),
                        NextState("BURST-RD"),
                    )
                # Otherwise initialize a new Burst.
                ).Else(
                    cs.eq(0),
                    NextState("BURST-CMD")
                )
            )
        )

        # TODO handle variable latency
        # TODO handle configurable latency

        fsm.act("BURST-CMD",
            cs.eq(1),
            source.valid.eq(1),
            addr.eq(bus.adr),
            source.data.eq(ca_bits[32:48]),
            source.len.eq(16),    
            source.mask.eq(0xFF),
            If(source.ready,
                NextValue(burst_adr, bus.adr),
                NextValue(burst_we, bus.we),
                NextState("BURST-ADDR"),
            )
        )

        fsm.act("BURST-ADDR",
            cs.eq(1),
            source.valid.eq(1),
            addr.eq(bus.adr),
            source.data.eq(ca_bits[0:32]),
            source.len.eq(32),    
            source.mask.eq(0xFF),
            NextValue(burst_cs, 1),
            NextValue(latency_cnt, _latency_cycles-2), # Latency count starts in the CA bits
            NextState("INITIAL-LATENCY"),
        )

        fsm.act("INITIAL-LATENCY",
            cs.eq(1),
            sink.ready.eq(1),
            source.valid.eq(1),    
            source.mask.eq(0),
            source.len.eq(16),
            NextValue(_extra_latency_flag, _extra_latency_flag | self.sink.rwds_bypass),
            NextValue(latency_cnt, latency_cnt - 1),
            If(latency_cnt == 0,
               
                # No Extra Latency
                If(_extra_latency_flag,
                    NextValue(latency_cnt, _latency_cycles),
                    NextState("SECOND-LATENCY"),

                # Extra Latency Cycle
                ).Else(
                    If(bus.we,
                        NextState("BURST-WR"),
                    ).Else(
                        NextValue(latency_cnt, 4),
                        NextState("WAIT"),
                    )
                )
            )
        )

        fsm.act("SECOND-LATENCY",
            cs.eq(1),
            source.valid.eq(1),    
            source.mask.eq(0),
            source.len.eq(16),
            NextValue(latency_cnt, latency_cnt - 1),
            If((latency_cnt == 0) & bus.we,
                NextState("BURST-WR"),
            ).Elif((latency_cnt == 1) & ~bus.we,
                NextValue(latency_cnt, 2),
                NextState("BURST-RD"),
            )
        )
        
        fsm.act("BURST-WR",
            cs.eq(1),
            sink.ready.eq(1),
            source.data.eq({"big": bus.dat_w, "little": reverse_bytes(bus.dat_w)}[endianness]),
            source.valid.eq(1),    
            source.mask.eq(0xFF),
            source.len.eq(32),
            source.rwds_en.eq(1),
            source.rwds.eq(0x0),
            If(source.ready,
                bus.ack.eq(1),
                NextValue(burst_adr, burst_adr + 1),
                NextState("IDLE"),
            )
        )

        fsm.act("BURST-RD",
            cs.eq(1),
            source.valid.eq(1),    
            source.mask.eq(0),
            source.len.eq(16),
            NextValue(latency_cnt, latency_cnt - 1),
            If(latency_cnt == 0,
                NextValue(latency_cnt, 4),
                NextState("WAIT"),
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
