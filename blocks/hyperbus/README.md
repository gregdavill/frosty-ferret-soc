## LiteX Hyperbus controller

Based on the architecture of LiteSPI. (https://github.com/litex-hub/litespi)

Notably CSR master controller, and Memory Mapped interface, each sharing a crossbar to a PHY layer.

PHY makes use of DDR I/O, and fixed delay elements to shift data into smapling window from RWDS signal.
