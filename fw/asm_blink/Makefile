
CROSS=riscv-none-elf-
CFLAGS:=-march=rv32i -mabi=ilp32 -Wl,-Bstatic,-T,sections.ld,--strip-debug -ffreestanding -nostdlib 
CFLAGS+=-I.

CC=$(CROSS)gcc
COPY=$(CROSS)objcopy
DUMP=$(CROSS)objdump

SRC=blink.s
TARGET=blink

.PHONY: all load clean

all: $(TARGET).bin

# ---- Final Target ----
$(TARGET).elf: $(SRC)
	$(CC) $(CFLAGS) -o $@ $(SRC)

# ---- Extra outputs ----
%.cde: %.elf
	$(COPY) -O verilog $< $@

%.bin: %.elf
	$(COPY) -O binary $< $@

%.disasm: %.elf
	$(DUMP) -dS --visualize-jumps $< > $@

load: blink.bin
# Load into FPGA FLASH @0x00000000
	ecpprog -o 0 blink.bin

# ---- Clean ----
clean:
	rm -f blink.bin blink.elf
