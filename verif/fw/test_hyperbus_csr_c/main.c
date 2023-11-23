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
    HYPERBUS0->config = (const hyperbusConfig_t){.hyperbus_enable=1,.latency_count=7,.latency_variable=false};
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
    HYPERBUS0->config = (const hyperbusConfig_t){.hyperbus_enable=1,.latency_count=7,.latency_variable=false};
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
    uin32_t mmap_value = *(volatile uint32_t*)0x30000000;
    if(0x1234abcf != mmap_value)
        return 3;

    /* Got to main, return 0 success */
    return 0;
}

/* ---- Helper Functions ---- */
/* ISRs will cause the CPU to jump here */
void isr() {

}
