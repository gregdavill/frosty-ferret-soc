`timescale 100ps / 100ps

module tb (
    output clk,
    input reset,
    input [4095:0] test_name
);


  wire spi0_clk;
  wire _spi0_clk;
  wire [3:0] spi0_dq;
  wire spi0_rwds;
  wire spi0_cs_n;


  dut dut (
      .clk(clk),
      .reset(reset),
      .spiflash4x_clk(_spi0_clk),
      .spiflash4x_cs_n(spi0_cs_n),
      .spiflash4x_dq(spi0_dq)
  );

  assign #15 spi0_clk = _spi0_clk;

  W25Q32JVxxIM FLASH (
      .CSn(spi0_cs_n),
      .CLK(spi0_clk),
      .DIO(spi0_dq[0]),
      .DO(spi0_dq[1]),
      .WPn(spi0_dq[2]),
      .HOLDn(spi0_dq[3]),
      .RESETn(~reset)
  );

  // Dump waves
  initial begin
    $dumpfile("dump.vcd");
    $dumpvars(0, tb);
  end

  initial begin
    repeat (5000) @(posedge clk);
    $error("Simulation Timeout");
    $finish();
  end


endmodule
