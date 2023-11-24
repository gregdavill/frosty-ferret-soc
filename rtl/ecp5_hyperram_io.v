//
// This file is part of frosty-ferret-soc
//
// Copyright (c) 2023 Greg Davill <greg.davill@gmail.com>
// SPDX-License-Identifier: BSD-2-Clause

`default_nettype none
`timescale 100ps / 100ps

module hyperbus_io(
    input clk,
    input rst,
    input [7:0] data0, // Rising clock edge output
    input [7:0] data1, // Falling clock edge output
    input [7:0] data_oe,

    input rwds0, // Rising clock edge output
    input rwds1,// Falling clock edge output
    input rwds_oe,

    output rwds_bypass,
    output [7:0] q0, // Rising edge input data
    output [7:0] q1, // Falling edge input data

    input clk_en,
    input cs_en,

    inout rwds_pad,
    inout [7:0] dq_pad,
    output clk_p_pad,
    output clk_n_pad,
    output reset_n,
    output cs_n,
    output debug
);


    localparam delay = 50;

    wire rwds_delayed;
    wire delay_code;

//    DDRDLLA u_ddrdll0 (
//        .CLK(clk),
//        .RST(~rst),
//        .UDDCNTLN(1'b0),
//        .FREEZE(1'b0),
//        .DDRDEL(delay_code),
//        .LOCK(),
//        .DCNTL0()
//    );

//    DLLDELD u_dlldel0 (
//        .A(rwds_pad), // Clock input
//        .DDRDEL(delay_code), // delay inputs
//        .LOADN(1'b0), // use delay inputs
//        .MOVE(),
//        .DIRECTION(),
//        .CFLAG(),
//        .Z(rwds_delayed) // Clock out
//    );

    delay_line #(
        .DELAY_LUTS(delay)
    ) u_delay0 (
        .A(rwds_pad),
        .Z(rwds_delayed)
    );

/*
    DELAYG #(
        .DEL_MODE("USER_DEFINED"),
        .DEL_VALUE(127)
    ) u_delayg0 (
        .A(rwds_pad),
        .Z(rwds_delayed)
    );
    */

    reg [7:0] dq_i_capt_r;
    reg [7:0] dq_i_capt_f;

    /* dq_i rwds_delay capture */
    always @(posedge rwds_delayed) begin
        dq_i_capt_r <= dq_pad;
    end

    always @(negedge rwds_delayed) begin
        dq_i_capt_f <= dq_pad;
    end

    /* Re-sync with main clock */
    reg [7:0] dq_i_resync_r;
    reg [7:0] dq_i_resync_f;
    always @(posedge clk) begin
        dq_i_resync_r <= dq_i_capt_r;
        dq_i_resync_f <= dq_i_capt_f;
    end
    assign q0 = dq_i_resync_r;
    assign q1 = dq_i_resync_f;


    reg rwds_r0, rwds_r1;
    /* rwds bypass, used for variable latency logic */
    always @(posedge clk) begin
        rwds_r0 <= rwds_delayed;
        rwds_r1 <= rwds_r0;
    end
    assign rwds_bypass = rwds_r1;

    /* DDR output path */
    reg rwds_o_capt_r;
    reg rwds_o_capt_f;
    reg rwds_o_capt_f0;
    reg rwds_oe0;
    wire rwds_o;

    always @(posedge clk) begin
        rwds_o_capt_r <= rwds0;
        rwds_o_capt_f0 <= rwds1;
        rwds_oe0 <= rwds_oe;
    end
    always @(negedge clk) begin
        rwds_o_capt_f <= rwds_o_capt_f0;
    end

    assign rwds_o = clk ? rwds_o_capt_r : rwds_o_capt_f;
    assign rwds_pad = rwds_oe0 ? rwds_o : 1'bz;



    /* DDR output path */
    reg [7:0] dq_o_capt_r;
    reg [7:0] dq_o_capt_f;
    reg [7:0] dq_o_capt_f0;
    wire [7:0] dq_o;

    always @(posedge clk) begin
        dq_o_capt_r <= data0;
        dq_o_capt_f0 <= data1;
    end
    always @(negedge clk) begin
        dq_o_capt_f <= dq_o_capt_f0;
    end
    assign dq_o = clk ? dq_o_capt_r : dq_o_capt_f;


    genvar i;
    generate
        for(i =0; i < 8; i++) begin
            reg oe;
            always @(posedge clk) begin
                oe <= data_oe[i];
            end

            assign dq_pad[i] = oe ? dq_o[i] : 1'bz;
        end
    endgenerate

    /* Clock output */
    wire clk_gated;

`ifdef COCOTB_SIM
    reg clk_en0;
    always @(posedge clk) begin
        clk_en0 <= clk_en;
    end

    assign clk_gated = clk_en0 ? clk : 0;
`else
    /* DCCA block used to remove clock glitch when enabling/disabling clock 
        ODDR1X would also work, but can't be LUT delayed before the I/O pins
    */
    DCCA u_dcca (
        .CLKI(clk),
        .CE(clk_en),
        .CLKO(clk_gated)
    );
`endif

//    DLLDELD u_dlldel1 (
//        .A(clk_gated), // Clock input
//        .DDRDEL(delay_code), // delay inputs
//        .LOADN(1'b0), // use delay inputs
//        .MOVE(),
//        .DIRECTION(),
//        .CFLAG(),
//        .Z(clk_pad) // Clock out
//    );

//    DLLDELD u_dlldel2 (
//        .A(~clk_gated), // Clock input
//        .DDRDEL(delay_code), // delay inputs
//        .LOADN(1'b0), // use delay inputs
//        .MOVE(),
//        .DIRECTION(),
//        .CFLAG(),
//        .Z(clk_n_pad) // Clock out
//    );

/*
    DELAYG #(
        .DEL_MODE("USER_DEFINED"),
        .DEL_VALUE(127)
    ) u_delayg1 (
        .A(clk_gated),
        .Z(clk_p_pad)
    );

    DELAYG #(
        .DEL_MODE("USER_DEFINED"),
        .DEL_VALUE(127)
    ) u_delayg2 (
        .A(~clk_gated),
        .Z(clk_n_pad)
    );
*/


    delay_line #(
        .DELAY_LUTS(delay)
    ) u_delay1 (
        .A(clk_gated),
        .Z(clk_p_pad)
    );
    
    delay_line #(
        .DELAY_LUTS(delay)
    ) u_delay2 (
        .A(~clk_gated),
        .Z(clk_n_pad)
    );

    /* Chip select */
    reg cs;
    always @(posedge clk) begin
        cs <= ~cs_en;
    end
    assign cs_n = cs;
    assign reset_n = ~rst;

    assign debug = dq_i_capt_r;


endmodule

module delay_line(
    input wire A,
    output wire Z
    );
	parameter DELAY_LUTS = 1;


    DELAYG #(
        .DEL_MODE("USER_DEFINED"),
        .DEL_VALUE(127)
    ) u_delayg0 (
        .A(A),
        .Z(Z)
    );
    
/*
	wire chain_wire[DELAY_LUTS+1:0];
	assign chain_wire[0] = A;
    
	assign Z = chain_wire[DELAY_LUTS+1];

	generate
		genvar i;
		for(i=0; i<=DELAY_LUTS; i=i+1) begin: delayline
			(* keep *) (* noglobal *)
			LUT4 #(.INIT(16'd2))
				chain_lut(.Z(chain_wire[i+1]), .A(chain_wire[i]), .B(0), .C(0), .D(0));
		end
    endgenerate
    
	*/
endmodule