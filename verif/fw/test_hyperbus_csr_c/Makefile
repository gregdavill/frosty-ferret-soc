
CROSS=riscv-none-elf-
CFLAGS:=-march=rv32i_zicsr -mabi=ilp32 -Wl,-Bstatic,-T,sections.ld,--strip-debug -ffreestanding -nostdlib -Os
CFLAGS+=-I. -I../../sim/build/software/include -I../../../deps/litex/litex/soc/cores/cpu/vexriscv -I../../../deps/litex/litex/soc/software/include -I../

CC=$(CROSS)gcc
COPY=$(CROSS)objcopy
DUMP=$(CROSS)objdump

SRC=start.s main.c
TARGET=test_hyperbus_csr_c

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
