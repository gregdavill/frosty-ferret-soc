
# Default to verilog
TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)

VERILOG_SOURCES=$(PWD)/dut.v $(PWD)/../../blocks/vexriscv/rtl/VexRiscv_Lite_rf.v $(PWD)/../../blocks/DFFRF_2R1W/DFFRF_2R1W.v $(PWD)/../tb/tb.v $(PWD)/../rtl/vendor_models/W25Q32JVxxIM.v
TOPLEVEL=tb
MODULE=tests

CUSTOM_COMPILE_DEPS = $(PWD)/dut.v

export DUT_CSRS=csr.csv

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: $(PWD)/dut.v
$(PWD)/dut.v:
	cp ../../build/gateware/dut.v ./dut.v
	cp ../../build/csr.csv ./csr.csv
	cp ../../build/gateware/*.init .
