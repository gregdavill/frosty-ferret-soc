#
# This file is part of LiteSPI
#
# Copyright (c) 2020 Antmicro <www.antmicro.com>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from migen.genlib.cdc import MultiReg

from litex.gen.genlib.misc import WaitTimer

from hyperbus.common import *

from litex.soc.interconnect import stream
from litex.soc.interconnect.csr import *

from litex.soc.integration.doc import AutoDoc


# HyperBus DDR PHY Core -----------------------------------------------------------------------------

class HyperBusDDRPHYCore(Module, AutoCSR, AutoDoc):
    """HyperBus PHY DDR instantiator

    The ``DDRHyperBusPHYCore`` class provides a generic PHY that can be connected to the ``HyperBusCore``.

    It supports single/dual/quad/octal output reads from the flash chips.

    You can use this class only with devices that supports the DDR primitives.

    The following diagram shows how each clock configuration option relates to outputs and input sampling in DDR mode:

    .. wavedrom:: ../../doc/ddr-timing-diagram.json

    Parameters
    ----------
    pads : Object
        SPI pads description.

    flash : SpiNorFlashModule
        SpiNorFlashModule configuration object.

    Attributes
    ----------
    source : Endpoint(spi_phy2core_layout), out
        Data stream.

    sink : Endpoint(spi_core2phy_layout), in
        Control stream.

    cs : Signal(), in
        Flash CS signal.
    """
    def __init__(self, pads, flash, cs_delay, extra_latency=0):
        self.source = source = stream.Endpoint(spi_phy2core_layout)
        self.sink   = sink   = stream.Endpoint(spi_core2phy_layout)
        self.cs     = Signal()

        self.rwds_bypass = Signal()

        # Clock Generator.
        clk_en = Signal()

        # CS control.
        cs_timer  = WaitTimer(cs_delay + 3) # Ensure cs_delay cycles between XFers.
        cs_enable = Signal()
        self.submodules += cs_timer
        self.comb += cs_timer.wait.eq(self.cs)
        self.comb += cs_enable.eq(cs_timer.done)

        # I/Os.
        dq_o  = Array([Signal(len(pads.dq)) for _ in range(2)])
        dq_i  = Array([Signal(len(pads.dq)) for _ in range(2)])
        dq_oe = Array([Signal(len(pads.dq)) for _ in range(2)])

        rwds_o  = Array([Signal(len(pads.rwds)) for _ in range(2)])
        rwds_oe = Array([Signal(len(pads.rwds)) for _ in range(2)])


        # Data Shift Registers.
        sr_cnt       = Signal(8, reset_less=True)
        sr_out_load  = Signal()
        sr_out_shift = Signal()
        sr_out       = Signal(len(sink.data), reset_less=True)
        rwds_out     = Signal(len(sink.rwds), reset_less=True)
        mask         = Signal(len(sink.mask), reset_less=True)
        rwds_en      = Signal(len(sink.rwds_en), reset_less=True)
        last         = Signal(reset_less=True)
        sr_in_shift  = Signal()
        sr_in        = Signal(len(sink.data), reset_less=True)

        # Lower level I/O block
        self.specials += [
            Instance("hyperbus_io",
                        i_clk=ClockSignal(),
                        i_rst=ResetSignal(),
                        i_data0=dq_o[0],
                        i_data1=dq_o[1],
                        i_data_oe=dq_oe[0],
                        i_rwds0=rwds_o[0],
                        i_rwds1=rwds_o[1],
                        i_rwds_oe=rwds_en,

                        o_rwds_bypass=source.rwds_bypass,
                        o_q0=dq_i[0],
                        o_q1=dq_i[1],

                        i_clk_en=clk_en,
                        i_cs_en=cs_enable,

                        io_rwds_pad=pads.rwds,
                        io_dq_pad=pads.dq,
                        o_clk_p_pad=pads.clk_p,
                        o_clk_n_pad=pads.clk_n,
                        o_reset_n=pads.reset_n,
                        o_cs_n=pads.cs_n
                        #o_debug=pads.debug
                    )
        ]

        # Data Out Shift.
        self.comb += [
            dq_o[0].eq(sr_out[-8:]),
            dq_o[1].eq(sr_out[-16:-8]),

            dq_oe[1].eq(mask),
            dq_oe[0].eq(mask),

            rwds_o[0].eq(rwds_out[-1:]),
            rwds_o[1].eq(rwds_out[-2:-1]),

            rwds_oe[1].eq(rwds_en),
            rwds_oe[0].eq(rwds_en),
        ]

        self.sync += If(sr_out_shift & ~sr_out_load,
            sr_out.eq(Cat(Constant(0, 16), sr_out)),
            rwds_out.eq(Cat(Constant(0, 2), rwds_out)),
        )

        self.submodules.fsm = fsm = FSM(reset_state="WAIT-CMD-DATA")

        self.sync += If(sr_out_load,
            sr_out.eq(sink.data << (len(sink.data) - sink.len)),
            rwds_out.eq(sink.rwds << (len(sink.rwds) - (sink.len >> 3))),
            last.eq(sink.last),
            mask.eq(sink.mask),
            rwds_en.eq(sink.rwds_en),
        
        # Tri-state outputs when IDLE
        ).Elif(fsm.ongoing("WAIT-CMD-DATA") & ~cs_enable,
            mask.eq(0),
            rwds_en.eq(0),
        )

        # Data In Shift.
        self.sync += If(sr_in_shift,
            sr_in.eq(Cat(dq_i[1][:8], dq_i[0][:8], sr_in)),
        )

        self.comb += [
            sink.ready.eq(sr_out_load),
        ]

        # FSM
        fsm.act("WAIT-CMD-DATA",
            # Stop Clk.
            NextValue(clk_en, 0),

            NextValue(source.valid, 0),
            NextValue(source.last, 0),

            # Wait for CS and a CMD from the Core.
            If(cs_enable & sink.valid,
                # Load Shift Register Count/Data Out.
                NextValue(sr_cnt, sink.len - 8*2),
                sr_out_load.eq(1),
                
                # Generate Clk.
                NextValue(clk_en,  1),
                
                # Start XFER.
                NextState("XFER")
            )
        )

        fsm.act("XFER",
            # Data In Shift.
            sr_in_shift.eq(1),

            # Data Out Shift.
            sr_out_shift.eq(1),

            # Shift Register Count Update/Check.
            NextValue(sr_cnt, sr_cnt - 8*2),
            # End XFer.
            If(sr_cnt == 0,
                # No more data?
                If(last | ~sink.valid,

                    # Stop Clk.
                    NextValue(clk_en, 0),
                    NextValue(sr_cnt, 8), # FIXME: Explain magic numbers.
                    NextState("XFER-END"),
                ).Else(
                    # Load Shift Register Count/Data Out.
                    NextValue(sr_cnt, sink.len - 8*2),
                    sr_out_load.eq(1),
                )
            ),
        )

        fsm.act("XFER-END",
            # Stop Clk.
            NextValue(clk_en, 0),

            # Data In Shift.
            sr_in_shift.eq(1),

            # Shift Register Count Update/Check.
            NextValue(sr_cnt, sr_cnt - 8),
            If(sr_cnt == 0,
                
                NextValue(sr_cnt, 0),
                If(cs_enable & sink.valid,
                    # Load Shift Register Count/Data Out.
                    NextValue(sr_cnt, sink.len - 8*2),
                    sr_out_load.eq(1),
                    
                    # Generate Clk.
                    NextValue(clk_en,  1),
                    
                    # Start XFER.
                    NextState("XFER")
                ).Else(
                    NextValue(source.valid, 1),
                    NextValue(source.last, 1),
                    NextState("WAIT-CMD-DATA"),
                )
            ),
        )

        self.comb += source.data.eq(sr_in)

