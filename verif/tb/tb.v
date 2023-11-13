//
// This file is part of frosty-ferret-soc
//
// Copyright (c) 2023 Greg Davill <greg.davill@gmail.com>
// SPDX-License-Identifier: BSD-2-Clause

`default_nettype none
`timescale 100ps / 100ps

module tb (
    input clk,
    input reset,
    input [4095:0] test_name
);

  wire spi0_clk;
  wire [3:0] spi0_dq;
  wire spi0_rwds;
  wire spi0_cs_n;

  wire wfi;
  wire [31:0] a0;

  dut dut (
      .clk(clk),
      .reset(reset),
      .spiflash4x_clk(spi0_clk),
      .spiflash4x_cs_n(spi0_cs_n),
      .spiflash4x_dq(spi0_dq)
  );

  W25Q32JVxxIM flash (
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

  // Extract wfi and a0
  assign wfi = dut.VexRiscv.lastStageInstruction == 32'h10500073;
  assign a0 = dut.VexRiscv.u_rf.regfile[10];


endmodule
