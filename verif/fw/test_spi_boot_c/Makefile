
CROSS=riscv-none-elf-
CFLAGS:=-march=rv32i_zicsr -mabi=ilp32 -Wl,-Bstatic,-T,sections.ld,--strip-debug -ffreestanding -nostdlib 
CFLAGS+=-I.

CC=$(CROSS)gcc
COPY=$(CROSS)objcopy
DUMP=$(CROSS)objdump

SRC=start.s main.c
TARGET=test_spi_boot_c

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
