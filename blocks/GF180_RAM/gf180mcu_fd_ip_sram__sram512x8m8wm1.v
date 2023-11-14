`timescale 1 ps / 1 ps

module gf180mcu_fd_ip_sram__sram512x8m8wm1 (
	CLK,
	CEN,
	GWEN,
	WEN,
	A,
	D,
	Q,
	VDD,
	VSS
);

input           CLK;
input           CEN;    //Chip Enable
input           GWEN;   //Global Write Enable
input   [7:0]     WEN;    //Write Enable
input   [8:0]     A;
input   [7:0]     D;
output  reg [7:0] Q;
inout       VDD;
inout       VSS;

reg	[7:0]	mem[512];

always @(posedge CLK) begin
    if(!CEN) begin
        if (GWEN) begin
            if(~(|WEN)) begin
                mem[A] <= D;
            end
        end
        else begin
            Q <= mem[A];
        end
    end
end

endmodule
