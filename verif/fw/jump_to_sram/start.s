.global main

.section .text.start
.global _start

_start:
  li a0,0x10000000
  jr a0
  nop
