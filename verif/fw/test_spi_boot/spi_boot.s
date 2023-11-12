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
    nop
    li a0, 0
    wfi
