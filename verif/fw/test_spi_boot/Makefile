
CROSS=riscv-none-elf-
CFLAGS:=-march=rv32i -mabi=ilp32 -Wl,-Bstatic,-T,sections.ld,--strip-debug -ffreestanding -nostdlib 
CFLAGS+=-I.

CC=$(CROSS)gcc
COPY=$(CROSS)objcopy
DUMP=$(CROSS)objdump

SRC=spi_boot.s
TARGET=test_spi_boot

.PHONY: all load clean

all: $(TARGET).bin $(TARGET).cde $(TARGET).disasm

# ---- Final Target ----
$(TARGET).elf: $(SRC)
	$(CC) $(CFLAGS) -o $@ $(SRC)

# ---- Extra outputs ----
%.cde: %.elf
	$(COPY) -O verilog $< $@
	sed -i 's/^@[[:digit:]]/@0/' $@

%.bin: %.elf
	$(COPY) -O binary $< $@

%.disasm: %.elf
	$(DUMP) -dS --visualize-jumps $< > $@

# ---- Clean ----
clean:
	rm -f $(TARGET).bin $(TARGET).elf $(TARGET).cde $(TARGET).disasm
