"""Fixed address map of the supported Z8 3.11 EG layout; offsets are bytes."""
BASE = 0x40160000
DATA_OFF, DATA_END, DATA_VA = 0x4B13000, 0x4DC0000, 0xA02808000

def ram(offset):
    return offset - DATA_OFF + DATA_VA
