//
// This file is part of frosty-ferret-soc
//
// Copyright (c) 2023 Greg Davill <greg.davill@gmail.com>
// SPDX-License-Identifier: BSD-2-Clause

`default_nettype none

module DFFRF_2R1W (
    input CLK,
    input WE,
    output reg [31:0] DA,
    output reg [31:0] DB,
    input [31:0] DW,
    input [4:0] RA,
    input [4:0] RB,
    input [4:0] RW
);

  (* no_rw_check , ram_style = "block" *) reg [31:0] regfile[32];

  always @(posedge CLK) begin
    DA <= regfile[RA];
    DB <= regfile[RB];
    if (WE) regfile[RW] <= DW;
  end

endmodule
