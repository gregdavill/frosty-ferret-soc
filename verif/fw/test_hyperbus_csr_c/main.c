#include <generated/csr.h>
#include <frostyferret.h>


int hyperram_read_id(){
    HYPERBUS0->ctrl = (const hyperbusCtrl_t){.reset=1};
    HYPERBUS0->config = (const hyperbusConfig_t){.hyperbus_enable=1,.latency_count=7,.latency_variable=false};
    HYPERBUS0->cmd = (HYPERBUS_CMD_READ | HYPERBUS_AREA_REG);
    HYPERBUS0->adr = 0;
    HYPERBUS0->ctrl = (const hyperbusCtrl_t){
        .adr_phase = true,
        .latency_phase = true,
        .read_phase = true,
        .start = true
    };
    while(HYPERBUS0->status.busy);

    return HYPERBUS0->rxtx;
}

int hyperram_write(uint32_t addr, uint32_t data){
    HYPERBUS0->ctrl = (const hyperbusCtrl_t){.reset=1};
    HYPERBUS0->config = (const hyperbusConfig_t){.hyperbus_enable=1,.latency_count=7,.latency_variable=false, .data_size=1};
    HYPERBUS0->cmd = (HYPERBUS_CMD_WRITE | HYPERBUS_AREA_MEM);
    HYPERBUS0->adr = addr;
    HYPERBUS0->rxtx = data;
    HYPERBUS0->ctrl = (const hyperbusCtrl_t){
        .adr_phase = true,
        .latency_phase = true,
        .write_phase = true,
        .start = true
    };
    while(HYPERBUS0->status.busy);

}

uint32_t hyperram_read(uint32_t addr){
    HYPERBUS0->ctrl = (const hyperbusCtrl_t){.reset=1};
    HYPERBUS0->config = (const hyperbusConfig_t){.hyperbus_enable=1,.latency_count=7,.latency_variable=false, .data_size=1};
    HYPERBUS0->cmd = (HYPERBUS_CMD_READ | HYPERBUS_AREA_MEM);
    HYPERBUS0->adr = addr;
    HYPERBUS0->ctrl = (const hyperbusCtrl_t){
        .adr_phase = true,
        .latency_phase = true,
        .read_phase = true,
        .start = true
    };
    while(HYPERBUS0->status.busy);

    return HYPERBUS0->rxtx;
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

uint32_t rand(void)
{
    static uint32_t state = 1;
    uint32_t x = state;
    x ^= x <<17;
    x ^= x >>7;
    x ^= x <<5;
    state = x;
    return x;
  }

/* ---- Main Function ---- */
int main() {

    uint16_t id = hyperram_read_id();

    if(id != 0x8f1f)
        return 1;

    hyperram_write(0x0, 0x1234abcf);
    uint32_t read_value;
    read_value = hyperram_read(0x0);

    if(0x1234abcf != read_value)
        return 2;

    /* Memory mapped read */
    uint32_t mmap_value = *(volatile uint32_t*)0x30000000;
    if(0xcfab3412 != mmap_value)
        return 3;

    /* MMAP write */
    *(volatile uint32_t*)0x30000010 = 0xAB22DE01;
    mmap_value = *(volatile uint32_t*)0x30000010;
    if(0xAB22DE01 != mmap_value)
        return 4;

    /* Back-to-back incrementing write */
    *(volatile uint32_t*)0x30000040 = 0xb3829dea;
    *(volatile uint32_t*)0x30000044 = 0x0391bcef;
    *(volatile uint32_t*)0x30000048 = 0x94751efa;
    *(volatile uint32_t*)0x3000004c = 0xabe5910d;

    if(*(volatile uint32_t*)0x30000040 != 0xb3829dea)
        return 5;
    if(*(volatile uint32_t*)0x30000044 != 0x0391bcef)
        return 6;
    if(*(volatile uint32_t*)0x30000048 != 0x94751efa)
        return 7;
    if(*(volatile uint32_t*)0x3000004c != 0xabe5910d)
        return 8;
    
    /* Test adjustable latency */
    // Model only supports 6-3 cycle latency
    // hyperram_cfg(0x8F0F | (((8) + 11) & 0xF) << 4); /* 8 cycle latency*/
    // HYPERBUS0->latency_cycles = 8;
    // *(volatile uint32_t*)0x30001000 = 0x4920baef;

    // if(*(volatile uint32_t*)0x30001000 != 0x4920baef)
    //     return 9;

    // hyperram_cfg(0x8F0F | (((7) + 11) & 0xF) << 4); /* 7 cycle latency*/
    // HYPERBUS0->latency_cycles = 7;
    // *(volatile uint32_t*)0x30001004 = 0x4920baef;

    // if(*(volatile uint32_t*)0x30001004 != 0x4920baef)
    //     return 10;

    hyperram_cfg(0x8F0F | (((6) + 11) & 0xF) << 4); /* 6 cycle latency*/
    HYPERBUS0->latency_cycles = 6;
    
    uint32_t v = rand();
    *(volatile uint32_t*)0x30001008 = v;
    if(*(volatile uint32_t*)0x30001008 != v)
        return 11;

    hyperram_cfg(0x8F0F | (((5) + 11) & 0xF) << 4); /* 5 cycle latency*/
    HYPERBUS0->latency_cycles = 5;
    
    v = rand();
    *(volatile uint32_t*)0x3000100c = v;
    if(*(volatile uint32_t*)0x3000100c != v)
        return 12;


    hyperram_cfg(0x8F0F | (((4) + 11) & 0xF) << 4); /* 4 cycle latency*/
    HYPERBUS0->latency_cycles = 4;
    
    v = rand();
    *(volatile uint32_t*)0x30001010 = v;
    if(*(volatile uint32_t*)0x30001010 != v)
        return 13;

    // Issue with test at 3-cycle latency
    // https://github.com/gregdavill/frosty-ferret-soc/issues/1
    
    // hyperram_cfg(0x8F0F | (((3) + 11) & 0xF) << 4); /* 3 cycle latency*/
    // HYPERBUS0->latency_cycles = 3;
    
    // v = rand();
    // *(volatile uint32_t*)0x30001014 = v;
    // if(*(volatile uint32_t*)0x30001014 != v)
    //     return 14;


    /* Got to main, return 0 success */
    return 0;
}

/* ---- Helper Functions ---- */
/* ISRs will cause the CPU to jump here */
void isr() {

}
