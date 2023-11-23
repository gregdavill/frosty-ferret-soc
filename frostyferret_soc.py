#!/usr/bin/env python3
#
# This file is part of frosty-ferret-soc
#
# Copyright (c) 2023 Greg Davill <greg.davill@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

# This variable defines all the external programs that this module
# relies on.  lxbuildenv reads this variable in order to ensure
# the build will finish without exiting due to missing third-party
# programs.

LX_DEPENDENCIES = ["riscv", "yosys"]

# Import lxbuildenv to integrate the deps/ directory
import lxbuildenv
import litex.soc.doc as lxsocdoc
from pathlib import Path
import subprocess
import sys
import os

from random import SystemRandom
import argparse

from migen import *
from migen.genlib.cdc import MultiReg, BlindTransfer, BusSynchronizer

from litex.build.generic_platform import *

from litex.soc.interconnect.csr import *
from litex.soc.interconnect.csr_eventmanager import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.integration.doc import AutoDoc, ModuleDoc

from litex.soc.integration.soc import SoCRegion


from rtl.sram import GF180_RAM
from rtl.platform.icebreaker_ppp import Platform as FPGAPlatform
from rtl.platform.sim import Platform as SimPlatform

from litex.soc.cores.led import LedChaser
from litespi.modules import W25Q32DW
from litespi.opcodes import SpiNorFlashOpCodes as Codes

# System constants ---------------------------------------------------------------------------------

boot_offset    = 0x0
bios_size      = 0x10000
SPI_FLASH_SIZE = 32 * 1024 * 1024
SRAM_EXT_SIZE  = 0x1000000
prefix = ""  # sometimes 'soc_', sometimes '' prefix Litex is attaching to net names

# FrostyFerretSoc -------------------------------------------------------------------------------------

class FrostyFerretSoc(SoCCore, AutoDoc):
    # I/O range: 0x80000000-0xfffffffff (not cacheable)
    SoCCore.mem_map = {
        "rom":             0x80000000, # uncached
        "sram":            0x10000000,
        "spiflash":        0x20000000,
        "hyperbus0":       0x30000000,
        "vexriscv_debug":  0xefff0000, # this doesn't "stick", LiteX overrides it, so if you use it, you will have to hard code it. Also, search & replace for changes.
        "csr":             0xf0000000,
    }

    def __init__(self, platform, sys_clk_freq=int(48e6),
                 **kwargs):

        reset_address = self.mem_map["spiflash"]
        
        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, sys_clk_freq, csr_data_width=32,
            integrated_rom_size  = 0,
            integrated_rom_init  = None, # bios_path,
            integrated_sram_size = 0, # Use external SRAM for boot code
            ident                = "",
            cpu_type             = "vexriscv",
            cpu_variant          = None,
            csr_paging           = 4096,  # increase paging to 1 page size
            csr_address_width    = 16,    # increase to accommodate larger page size
            with_uart            = True, # implemented manually to allow for UART mux
            uart_baudrate        = 2000000,
            cpu_reset_address    = reset_address,
            with_ctrl            = True,
            with_timer           = True,
            **kwargs)
        # Litex will always try to move the ROM back to 0.
        # Move ROM and RAM to uncached regions - we only use these at boot, and they are already quite fast
        # this helps remove their contribution from the cache tag critical path
        if self.mem_map["rom"] == 0:
            self.mem_map["rom"] += 0x80000000

        self.cpu.use_external_variant("blocks/vexriscv/rtl/VexRiscv_Lite_rf.v")
        self.platform.add_source("blocks/DFFRF_2R1W/DFFRF_2R1W.v")

        #GF180_RAM
        sram_size = 2 * 1024
        sram = self.submodules.mem = GF180_RAM(size=sram_size)
#        self.register_mem("sram", self.mem_map["sram"], self.mem.bus, sram_size)
        self.bus.add_slave("sram", self.mem.bus, SoCRegion(origin=self.mem_map["sram"], size=sram_size))

        self.platform.add_source("blocks/GF180_RAM/GF180_RAM_512x32.v")
        self.platform.add_source("blocks/GF180_RAM/gf180_ram_512x8_wrapper.v")
        self.platform.add_source("blocks/GF180_RAM/gf180mcu_fd_ip_sram__sram512x8m8wm1.v")


        # Fix the location of CSRs and IRQs so we can do firmware updates between generations of the SoC
        self.csr.locs = {
            # 'reboot': 0,
            # 'timer0': 1,
            # 'crg': 2,
            # 'gpio': 3,
            # 'ctrl': 4,
            # 'uart': 5,
            # 'spiflash_core': 6,
            # 'spiflash_phy': 7,
            # 'hyperbus0_core': 8,
            # 'hyperbus0_phy': 9,
            # 'leds': 10,
        }

        self.irq.locs = {
            'timer0': 0,
            'gpio': 1,
        }

        self.submodules.crg = platform.crg(platform, sys_clk_freq)

        self.leds = LedChaser(
            pads         = platform.request_all("user_led"),
            sys_clk_freq = sys_clk_freq)

        self.add_spi_flash(mode="4x", module=W25Q32DW(Codes.READ_1_1_1), with_master=True)


        self.platform.add_source("rtl/ecp5_hyperram_io.v")
        # Add HyperBus
        # PHY
        from hyperbus.phy.generic import HyperBusPHY
        from hyperbus import HyperBus
        self.hyperbus0_phy = HyperBusPHY(self.platform.request("hyperbus0"))
        # Core
        hyperbus0_core = HyperBus(self.hyperbus0_phy, mmap_endianness=self.cpu.endianness, **kwargs)
        self.add_module(name=f"hyperbus0_core", module=hyperbus0_core)
        spiflash_region = SoCRegion(origin=self.mem_map.get("hyperbus0", None), size=0x10000000)
        self.bus.add_slave("hyperbus0", slave=hyperbus0_core.bus, region=spiflash_region)


        self.do_finalize()

# Build --------------------------------------------------------------------------------------------

def main():
    from litex.build.parser import LiteXArgumentParser
    parser = LiteXArgumentParser(platform=FPGAPlatform, description="LiteX SoC")
    parser.add_target_argument("--flash",               action="store_true",      help="Flash Bitstream and BIOS.")
    parser.add_target_argument("--sim",               action="store_true",      help="Flash Bitstream and BIOS.")
    args = parser.parse_args()

    if args.sim:
        platform = SimPlatform()
    else:
        platform = FPGAPlatform()

    ##### define the soc
    soc = FrostyFerretSoc(
        platform,
    )

    ##### setup the builder and run it
    builder = Builder(soc, output_dir="build",
        csr_csv="build/csr.csv", csr_svd="build/software/soc.svd",
        compile_software=args.build, compile_gateware=args.build)
    #builder.software_packages=[] # necessary to bypass Meson dependency checks required by Litex libc

    if args.sim:
        vns = builder.build(run=False)
        return 0
    
    vns = builder.build()
    soc.do_exit(vns)
    lxsocdoc.generate_docs(soc, "build/documentation", note_pulses=True, quiet=True, sphinx_extensions=['sphinx_verilog_domain'])
    os.system("sphinx-build -M html build/documentation/ build/documentation/_build")
        
    
    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(builder.get_bitstream_filename(mode="sram", ext=".bit")) 


    return 0

if __name__ == "__main__":
    from datetime import datetime
    start = datetime.now()
    ret = main()
    print("Run completed in {}".format(datetime.now()-start))

    sys.exit(ret)