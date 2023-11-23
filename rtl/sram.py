from migen import *
from litex.soc.interconnect import wishbone

kB = 1024

class GF180_RAM(Module):
    def __init__(self, width=32, size=2 * kB):
        self.bus = wishbone.Interface(width)

        # # #
        assert width in [32]
        assert size in [2 * kB]
        depth_cascading = size // (2 * kB)
        width_cascading = 1

        # Combine RAMs to increase Depth.
        # for d in range(depth_cascading):
        #     # Combine RAMs to increase Width.
        #     for w in range(width_cascading):
        datain = Signal(32)
        dataout = Signal(32)
        maskwren = Signal(4)
        wren_b = Signal()
        cs_b = Signal()

        # ro port signals
        self.clk1 = Signal()
        self.cs_b1 = Signal()
        self.adr1 = Signal(9)
        self.dataout1 = Signal(32)

        self.comb += [
            datain.eq(self.bus.dat_w[0:32]),
            wren_b.eq(~(self.bus.we & self.bus.stb & self.bus.cyc)),
            self.bus.dat_r[0:32].eq(dataout),
            cs_b.eq(ResetSignal()),  # rstn is normally high -> cs_b low
            # ),
            # maskwren is nibble based
            maskwren[0].eq(self.bus.sel[0]),
            maskwren[1].eq(self.bus.sel[1]),
            maskwren[2].eq(self.bus.sel[2]),
            maskwren[3].eq(self.bus.sel[3]),
        ]
        self.specials += Instance("GF180_RAM_512x32",
                                  i_CLK=ClockSignal("sys"),
                                  i_A=self.bus.adr[:9],
                                  i_D=datain,
                                  i_GWEN=wren_b,
                                  i_WEN=~maskwren,
                                  i_CEN=cs_b,
                                  o_Q=dataout,
                                  )

        self.sync += self.bus.ack.eq(self.bus.stb & self.bus.cyc & ~self.bus.ack)
