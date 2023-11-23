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

  wire hyperbus0_clk_p;
  wire hyperbus0_clk_n;
  wire hyperbus0_cs_n;
  wire [7:0] hyperbus0_dq;
  wire hyperbus0_reset_n;
  wire hyperbus0_rwds;

  wire wfi;
  wire [31:0] a0;

  dut dut (
      .clk(clk),
      .reset(reset),
      .spiflash4x_clk(spi0_clk),
      .spiflash4x_cs_n(spi0_cs_n),
      .spiflash4x_dq(spi0_dq),
      .hyperbus0_clk_p(hyperbus0_clk_p),
      .hyperbus0_clk_n(hyperbus0_clk_n),
      .hyperbus0_cs_n(hyperbus0_cs_n),
      .hyperbus0_dq(hyperbus0_dq),
      .hyperbus0_reset_n(hyperbus0_reset_n),
      .hyperbus0_rwds(hyperbus0_rwds)
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

s27ks0641 hyerram (
    .DQ7(hyperbus0_dq[7]),
    .DQ6(hyperbus0_dq[6]),
    .DQ5(hyperbus0_dq[5]),
    .DQ4(hyperbus0_dq[4]),
    .DQ3(hyperbus0_dq[3]),
    .DQ2(hyperbus0_dq[2]),
    .DQ1(hyperbus0_dq[1]),
    .DQ0(hyperbus0_dq[0]),
    .RWDS(hyperbus0_rwds),
    .CSNeg(hyperbus0_cs_n),
    .CK(hyperbus0_clk_p),
    .CKNeg(hyperbus0_clk_n),
    .RESETNeg(hyperbus0_reset_n)
);

  // Dump waves
  initial begin
    $dumpfile("dump.vcd");
    $dumpvars(0, tb);
  end

  // Extract wfi and a0
  assign wfi =   (dut.VexRiscv.lastStageInstruction == 32'h10500073) 
              && (dut.VexRiscv.lastStageIsValid);
  assign a0 = dut.VexRiscv.u_rf.regfile[10];


endmodule
