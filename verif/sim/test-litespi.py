# Tests for the Fomu Tri-Endpoint
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, NullTrigger, Timer, ClockCycles

import logging
import csv

class SpiTest:
    def __init__(self, dut):
        self.dut = dut
        self.csrs = dict()
        with open("csr.csv", newline='') as csr_csv_file:
            csr_csv = csv.reader(csr_csv_file)
            # csr_register format: csr_register, name, address, size, rw/ro
            for row in csr_csv:
                if row[0] == 'csr_register':
                    self.csrs[row[1]] = int(row[2], base=0)
        cocotb.start_soon(Clock(dut.clk, 10, 'ns').start())

        # Set the signal "test_name" to match this test
        import inspect
        tn = cocotb.binary.BinaryValue(value=None, n_bits=4096)
        tn.buff = bytes(inspect.stack()[1][3], encoding='ascii')
        self.dut.test_name.value = tn

    @cocotb.coroutine
    def reset(self):
        self.dut.reset.value = 1
        yield RisingEdge(self.dut.clk)
        yield RisingEdge(self.dut.clk)
        self.dut.reset.value = 0
        yield RisingEdge(self.dut.clk)

    @cocotb.coroutine
    def clock_cycles(self, cycles: int):
        yield ClockCycles(self.dut.clk, cycles)


@cocotb.test()
# @cocotb.coroutine
def test_basic(dut):
    """Test basic"""
    harness = SpiTest(dut)
    yield harness.reset()

    yield harness.clock_cycles(2000)
    