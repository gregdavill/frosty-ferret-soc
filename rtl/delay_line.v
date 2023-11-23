

module delay_line(
    input wire A,
    output wire Z
    );
	parameter DELAY_LUTS = 1;

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
	
endmodule