//
// This file is part of frosty-ferret-soc
//
// Copyright (c) 2023 Greg Davill <greg.davill@gmail.com>
// SPDX-License-Identifier: BSD-2-Clause

`default_nettype none
`timescale 100ps / 100ps

module DELAYG(
	input A,
	output Z
);
	parameter DEL_MODE = "USER_DEFINED";
	parameter DEL_VALUE = 0;

    
    assign #5 Z = A;

endmodule