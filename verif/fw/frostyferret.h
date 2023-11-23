

#ifndef FROSTYFERRET_H_
#define FROSTYFERRET_H_

#include <stdint.h>
#include <stdbool.h>

typedef struct  {
    uint32_t start : 1;
    uint32_t reset : 1;
    uint32_t resevered0 : 6;
    uint32_t adr_phase : 1;
    uint32_t latency_phase : 1;
    uint32_t read_phase : 1;
    uint32_t write_phase : 1;
    uint32_t reserved1 : 27;

} hyperbusCtrl_t;

typedef struct {
    uint32_t idle : 1;
    uint32_t busy : 1;
} hyperbusStatus_t;

typedef struct {
    uint32_t hyperbus_enable : 1;
    uint32_t latency_variable : 1;
    uint32_t reserved0 : 14;
    uint32_t latency_count : 4;
} hyperbusConfig_t;

typedef struct {
    volatile uint32_t mmap_dummy;
    volatile uint32_t cs;
    volatile uint32_t rxtx;
    volatile uint32_t reserved;
    volatile hyperbusConfig_t config;
    volatile uint32_t cmd;
    volatile uint32_t adr;
    volatile hyperbusCtrl_t ctrl;
    volatile hyperbusStatus_t status;
} hyperbus_t;

#define HYPERBUS_CMD_READ 0x8000
#define HYPERBUS_CMD_WRITE 0x0000
#define HYPERBUS_AREA_MEM 0x0000
#define HYPERBUS_AREA_REG 0x4000


#define HYPERBUS0 ((hyperbus_t*)(0xf0001000))

#endif