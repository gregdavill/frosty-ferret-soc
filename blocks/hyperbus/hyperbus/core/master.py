#
# This file is part of LiteSPI
#
# Copyright (c) 2020 Antmicro <www.antmicro.com>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from migen.genlib.fsm import FSM, NextState

from litex.soc.interconnect import stream
from litex.soc.interconnect.csr import *

from hyperbus.common import *


class HyperBusMaster(Module, AutoCSR):
    """DDR Hyperbus Master

    The ``HyperBusMaster`` class provides a DDR Hyperbus master that can be controlled using CSRs.

    It supports multiple access modes with help of ``width`` and ``mask`` registers which can be used to configure the PHY into any supported SDR mode (single/dual/quad/octal).

    Parameters
    ----------
    fifo_depth : int
        Depth of the internal TX/RX FIFO.

    cs_width : int
        Number of CS lines to support.

    Attributes
    ----------
    source : Endpoint(spi_phy2core_layout), out
        Data stream.

    sink : Endpoint(spi_core2phy_layout), in
        Control stream.

    cs : Signal(), out
        Slave CS signal.

    """

    def __init__(self, cs_width=1, tx_fifo_depth=1, rx_fifo_depth=1):
        self.sink = stream.Endpoint(spi_phy2core_layout)
        self.source = stream.Endpoint(spi_core2phy_layout)
        self.cs = Signal(cs_width)
        assert self.sink.data.nbits == self.source.data.nbits

        self._cs = CSRStorage(cs_width)

        self._rxtx = CSR(self.source.data.nbits)
        self._status = CSRStatus(
            fields=[
                CSRField(
                    "tx_ready", size=1, offset=0, description="TX FIFO is not full."
                ),
                CSRField(
                    "rx_ready", size=1, offset=1, description="RX FIFO is not empty."
                ),
            ]
        )

        self._hyperbus_cfg = CSRStorage(
            fields=[
                CSRField(
                    "hyperbus",
                    size=1,
                    offset=0,
                    description="Hyperbus enable (set bits to ``1`` to enable hyperbus mode)",
                ),
                CSRField(
                    "latency_variable",
                    size=1,
                    offset=1,
                    reset=0b0,
                    description="Control the latency between cmd and data phase",
                    values=[
                        ("0b0", "Variable Latency"),
                        ("0b1", "Fixed Latency"),
                    ],
                ),
                CSRField(
                    "latency_count",
                    size=4,
                    offset=16,
                    reset=7,
                ),
            ],
            description="hyperbus config.",
        )

        self._hyperbus_cmd = CSRStorage(
            fields=[
                CSRField(
                    "command", size=16, offset=0, description="Hyperbus Command"
                ),
                CSRField("data", size=16, offset=16, description="Hyperbus Data"),
            ],
            description="hyperbus Command.",
        )

        self._hyperbus_adr = CSRStorage(
            fields=[
                CSRField(
                    "address", size=32, offset=0, description="Hyperbus Address"
                ),
            ],
            description="hyperbus Address.",
        )

        self._hyperbus_ctrl = CSRStorage(
            fields=[
                CSRField(
                    "start",
                    size=1,
                    offset=0,
                    pulse=True,
                    description="Start a transaction",
                ),
                CSRField(
                    "reset",
                    size=1,
                    offset=1,
                    pulse=True,
                    description="Reset internal state",
                ),
                # CSRField('cmd_phase',  size=1, offset=16, reset=0b1, description='Enable CMD phase'),
                CSRField(
                    "adr_phase",
                    size=1,
                    offset=8,
                    reset=0b1,
                    description="Enable ADR phase",
                ),
                CSRField(
                    "latency_phase",
                    size=1,
                    offset=9,
                    reset=0b1,
                    description="Enable latency phase",
                ),
                CSRField(
                    "data_read_phase",
                    size=1,
                    offset=10,
                    reset=0b1,
                    description="Enable data phase",
                ),
                CSRField(
                    "data_write_phase",
                    size=1,
                    offset=11,
                    reset=0b0,
                    description="Enable data phase",
                ),
            ],
            description="hyperbus control.",
        )

        self._hyperbus_status = CSRStatus(
            fields=[
                CSRField(
                    "idle", size=1, offset=0, description="Master interface is IDLE"
                ),
                CSRField(
                    "busy", size=1, offset=1, description="Master interface is BUSY"
                ),
            ]
        )

        # # #

        # FIFOs.
        tx_fifo = stream.SyncFIFO(spi_core2phy_layout, depth=tx_fifo_depth)
        rx_fifo = stream.SyncFIFO(spi_phy2core_layout, depth=rx_fifo_depth)
        self.submodules += tx_fifo, rx_fifo
        

        # # SPI CS.
        # self.comb += self.cs.eq(self._cs.storage)

        # # SPI TX (MOSI).
        self.comb += [
            tx_fifo.sink.valid.eq(self._rxtx.re),
            self._status.fields.tx_ready.eq(tx_fifo.sink.ready),
            tx_fifo.sink.data.eq(self._rxtx.r),
            tx_fifo.sink.rwds.eq(0x0),
            tx_fifo.sink.rwds_en.eq(0x3),
            tx_fifo.sink.len.eq(32),
            tx_fifo.sink.width.eq(8),
            tx_fifo.sink.mask.eq(0xFF),
            tx_fifo.sink.last.eq(1),
        ]


        # Hyperbus
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        self.comb += [
        ]

        # Status
        self.comb += [
            self._hyperbus_status.fields.idle.eq(fsm.ongoing("IDLE")),
            self._hyperbus_status.fields.busy.eq(~fsm.ongoing("IDLE")),
        ]

        _latency_cnt = Signal(4)
        _latency_flag = Signal()

        # FSM.
        delay_cnt = Signal(4)
        fsm.act(
            "IDLE",
            self.source.valid.eq(False),
            self.source.data.eq(0),
            self.source.len.eq(0),
            self.source.width.eq(0),
            self.source.mask.eq(0),
            # Wait for start from CSR
            If(self._hyperbus_ctrl.fields.start,
                If(self._hyperbus_ctrl.fields.data_write_phase,
                    If(tx_fifo.source.valid, 
                       NextState("CMD_PHASE")
                    ).Else(
                        NextState("TX_DATA_WAIT"),
                    ),
                ).Else(
                    NextState("CMD_PHASE"),
                ),
            ),
        )

        fsm.act(
            "TX_DATA_WAIT",
            self.source.valid.eq(False),
            self.source.data.eq(0),
            self.source.len.eq(0),
            self.source.width.eq(0),
            self.source.mask.eq(0),
            # Wait for data in tx_fifo from CSR
            If(
                self._rxtx.re | tx_fifo.source.valid,
                NextState("CMD_PHASE"),
            ),
        )

        fsm.act(
            "CMD_PHASE",
            self.source.valid.eq(True),
            self.source.data.eq(self._hyperbus_cmd.fields.command),
            self.source.len.eq(16),
            self.source.width.eq(8),
            self.source.mask.eq(0xFF),
            If(self.source.ready,
                If(
                    self._hyperbus_ctrl.fields.adr_phase,
                    NextState("ADR_PHASE"),
                ).Else(
                    NextState("IDLE"),
                ),
            ),
        )

        fsm.act(
            "ADR_PHASE",
            self.source.valid.eq(True),
            self.source.data.eq(self._hyperbus_adr.fields.address),
            self.source.len.eq(32),
            self.source.width.eq(8),
            self.source.mask.eq(0xFF),
            If(
                self.source.ready,
                If(
                    self._hyperbus_ctrl.fields.latency_phase,
                    NextState("LATENCY"),
                    NextValue(_latency_flag, 0),
                    If(
                        self._hyperbus_ctrl.fields.data_read_phase,
                        NextValue(_latency_cnt, 7 - 2),
                    ).Else(
                        NextValue(_latency_cnt, 7 - 3),
                    ),
                )
                .Elif(
                    self._hyperbus_ctrl.fields.data_read_phase,
                    NextState("READ_DATA"),
                )
                .Elif(
                    self._hyperbus_ctrl.fields.data_write_phase,
                    NextState("WRITE_DATA"),
                )
                .Else(
                    NextState("IDLE"),
                ),
            ),
        )

        fsm.act(
            "LATENCY",
            self.source.valid.eq(True),
            self.source.data.eq(0),
            self.source.len.eq(16),
            self.source.width.eq(8),
            self.source.mask.eq(0),
            NextValue(_latency_flag, _latency_flag | self.sink.rwds_bypass),
            If(
                _latency_cnt == 0,
                If(
                    ~_latency_flag,
                    If(
                        self._hyperbus_ctrl.fields.data_read_phase,
                        NextState("READ_DATA"),
                    ).Elif(
                        self._hyperbus_ctrl.fields.data_write_phase,
                        NextState("WRITE_DATA"),
                    ),
                ).Else(
                    NextState("SECOND_LATENCY"),
                    NextValue(_latency_cnt, 7 - 1),
                ),
            ).Else(
                NextValue(_latency_cnt, _latency_cnt - 1),
            ),
        )

        fsm.act(
            "SECOND_LATENCY",
            self.source.valid.eq(True),
            self.source.data.eq(0),
            self.source.len.eq(16),
            self.source.width.eq(8),
            self.source.mask.eq(0),
            If(
                _latency_cnt == 0,
                If(
                    self._hyperbus_ctrl.fields.data_read_phase,
                    NextState("READ_DATA"),
                )
                .Elif(
                    self._hyperbus_ctrl.fields.data_write_phase,
                    NextState("WRITE_DATA"),
                )
                .Else(
                    NextState("IDLE"),
                ),
            ).Else(
                NextValue(_latency_cnt, _latency_cnt - 1),
            ),
        )

        fsm.act(
            "READ_DATA",
            self.source.valid.eq(True),
            self.source.data.eq(0),
            self.source.len.eq(16),
            self.source.width.eq(8),
            self.source.mask.eq(0),
            If(
                self.source.ready,
                NextValue(delay_cnt, 4),
                NextState("FIN")
                # )
            ),
        )

        fsm.act(
            "WRITE_DATA",
            tx_fifo.source.connect(self.source),
            If(
                ~tx_fifo.source.valid,
                NextValue(delay_cnt, 1),
                NextState("FIN"),
            ),
        )

        fsm.act(
            "FIN",
            self.source.valid.eq(False),
            self.source.data.eq(0),
            self.source.len.eq(0),
            self.source.width.eq(0),
            self.source.mask.eq(0),
            NextValue(delay_cnt, delay_cnt - 1),
            If(
                delay_cnt == 0,
                NextState("IDLE"),
            ),
        )

        self.comb += self.cs.eq(~fsm.ongoing("IDLE") & ~fsm.ongoing("TX_DATA_WAIT"))

        # SPI RX (MISO).
        self.comb += [
            If(fsm.ongoing("READ_DATA") | fsm.ongoing("FIN"),
               self.sink.connect(rx_fifo.sink)
            ).Else(
                self.sink.ready.eq(1),
            ),

            rx_fifo.source.ready.eq(self._rxtx.we),
            self._status.fields.rx_ready.eq(rx_fifo.source.valid),
            self._rxtx.w.eq(rx_fifo.source.data),
        ]
