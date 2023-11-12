.section .text.start
.global _start

_start:
  j init
  nop
  nop
  nop
  nop
  nop
  nop
  nop

init:
    li t0, 0xf0008000
    li t1, 2
loop:
    sw zero,0(t0) # LED OFF
    sw t1,0(t0)   # LED ON
    j loop
