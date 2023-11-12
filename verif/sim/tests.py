#
# This file is part of frosty-ferret-soc
#
# Copyright (c) 2023 Greg Davill <greg.davill@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.result import SimTimeoutError, SimFailure, TestSuccess
from cocotb.handle import HierarchyObject

import logging
import os
import csv


class SoCTestHarness:
    def __init__(self, dut: HierarchyObject):
        """Create instance of SoCTestHarness. This provides easy reuse of functions around the DUT

        Args:
            dut (HierarchyObject): Pass through DUT form each cocotb test
        """
        self.dut = dut
        self.csrs = dict()
        self.timeout_cycles = 50000

        self._set_test_name()
        self._load_csr("csr.csv")

        cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
        cocotb.start_soon(self._test_timeout())

    # Harness internal functions
    def _load_csr(self, csr_filename: str):
        """Load csrs into a local variable so that they can be accessed directly in tests

        Args:
            csr_filename (str): filename of csr csv file
        """
        with open(csr_filename, newline="") as csr_csv_file:
            csr_csv = csv.reader(csr_csv_file)
            # csr_register format: csr_register, name, address, size, rw/ro
            for row in csr_csv:
                if row[0] == "csr_register":
                    self.csrs[row[1]] = int(row[2], base=0)

    def _set_test_name(self):
        """Set the testname into a variable visible in gtkwave"""
        import inspect

        tn = cocotb.binary.BinaryValue(value=None, n_bits=4096)
        tn.buff = bytes(inspect.stack()[1][3], encoding="ascii")
        self.dut.test_name.value = tn

    @cocotb.coroutine
    async def _test_timeout(self):
        """coroutine started by the harness. Will fail a test if self.timeout_cycles elapses.

        Raises:
            SimTimeoutError: When simulation has timed out
        """
        await ClockCycles(self.dut.clk, self.timeout_cycles)
        raise SimTimeoutError(f"Timeout after {self.timeout_cycles} cycles")

    @cocotb.coroutine
    def wfi(self):
        """Wait for a 'wfi' instruction to be executed, then check return value (a0)

        Firmware can make use of this to issue a runtime error back to the simulation.

        Raises:
            TestSuccess: When a0 == 0
            SimFailure: When a0 != 0
        """
        yield RisingEdge(self.dut.wfi)
        if int(self.dut.a0.value) == 0:
            raise TestSuccess()
        else:
            self.dut.a0._log.error(
                f"Non-zero return code: (a0={int(self.dut.a0.value)})"
            )
            raise SimFailure()

    # Harness public functions for tests
    @cocotb.coroutine
    def reset(self):
        """Toggle the reset on the DUT, and wait for a clock edge"""
        self.dut.reset.value = 1
        yield RisingEdge(self.dut.clk)
        yield RisingEdge(self.dut.clk)
        self.dut.reset.value = 0
        yield RisingEdge(self.dut.clk)

    def build_fw(self, firmware_name: str):
        """Builds firmware

        Args:
            firmware_name (str): Firmware name to build
        """
        os.system(f"make -C ../fw/{firmware_name} {firmware_name}.bin")

    def init_spiflash(self, firmware_name: str):
        with open(f"../fw/{firmware_name}/{firmware_name}.bin", "rb") as f:
            for i, b in enumerate(f.read()):
                self.dut.flash.memory[i].value = b

    @cocotb.coroutine
    def clock_cycles(self, cycles: int):
        """Wait for number of DUT clock cycles

        Args:
            cycles (int): cycles to wait for
        """
        yield ClockCycles(self.dut.clk, cycles)


@cocotb.test()
def test_spi_boot(dut):
    """Test SPI boot on POR"""
    harness = SoCTestHarness(dut)
    harness.build_fw("test_spi_boot")
    harness.init_spiflash("test_spi_boot")
    yield harness.reset()
    yield harness.wfi()


@cocotb.test()
def test_spi_boot_c(dut):
    """Test C firmware SPI boot into main"""
    harness = SoCTestHarness(dut)
    harness.build_fw("test_spi_boot_c")
    harness.init_spiflash("test_spi_boot_c")
    yield harness.reset()
    yield harness.wfi()
