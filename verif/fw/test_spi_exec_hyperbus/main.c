
#include <stdint.h>
#include <frostyferret.h>

__attribute__((used, section(".hyperbus_mem")))
int hyperbus_main() {
    /* This function executed from MMAP Hyperbus */
    __asm__ volatile("nop");

    /* Mark test a success */
    __asm__ volatile("li a0, 0");
    __asm__ volatile("wfi");
    
    return 0;
}

void hyperram_cfg(uint32_t cfg){
    HYPERBUS0->config = (const hyperbusConfig_t){.hyperbus_enable=1,.latency_count=7,.latency_variable=false, .data_size=0};
    HYPERBUS0->cmd = (HYPERBUS_CMD_WRITE | HYPERBUS_AREA_REG);
    HYPERBUS0->adr = 0x01000000;    
    HYPERBUS0->rxtx = cfg;
    HYPERBUS0->ctrl = (const hyperbusCtrl_t){
        .adr_phase = true,
        .write_phase = true,
        .start = true
    };

    while(HYPERBUS0->status.busy);
}


// From linker
extern uint32_t hyperbus_start;
extern uint32_t hyperbus_end;

/* ---- Main Function ---- */
void main() {

    hyperram_cfg(0x8F0F | (((4) + 11) & 0xF) << 4); /* 4 cycle latency*/
    HYPERBUS0->latency_cycles = 4;

    volatile uint32_t* ptr = (uint32_t*)&hyperbus_start;
    volatile uint32_t* end = (uint32_t*)&hyperbus_end;
    
    volatile uint32_t* dest = (volatile uint32_t*)0x30000000;

    while(ptr < end){
        *dest++ = *ptr++;
    }

    __asm__ volatile ("li a0,0x30000000");
    __asm__ volatile ("jr a0");
}

/* ---- Helper Functions ---- */
/* ISRs will cause the CPU to jump here */
void isr() {

}
