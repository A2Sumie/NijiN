"""Minimal AArch64 encoder for the handful of instruction forms the ProRes menu patch needs.

Every emitted word is disassembled again with Capstone by the caller (`Block.listing`), so a wrong
encoding shows up as text that differs from what was asked for.  Offline only.
"""
import struct


def _imm(value, bits, signed=False):
    lo, hi = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if signed else (0, (1 << bits) - 1)
    if not lo <= value <= hi:
        raise ValueError(f'immediate {value:#x} does not fit {bits} bits')
    return value & ((1 << bits) - 1)


class Block:
    """Code assembled for one fixed virtual address; labels resolve on `bytes()`."""

    def __init__(self, va):
        self.va, self.items, self.labels = va, [], {}

    @property
    def here(self):
        return self.va + 4 * len(self.items)

    def label(self, name):
        if name in self.labels:
            raise ValueError('duplicate label ' + name)
        self.labels[name] = self.here

    def _w(self, word):
        self.items.append(word)

    def _rel(self, make):
        """Instruction whose immediate depends on a label or absolute target."""
        self.items.append((self.here, make))

    def _target(self, target):
        return self.labels[target] if isinstance(target, str) else target

    # ---- moves -------------------------------------------------------
    def mov_w(self, rd, value):
        """mov wN,#imm16"""
        self._w(0x52800000 | _imm(value, 16) << 5 | rd)

    def mov_x64(self, rd, value):
        """Four-instruction 64-bit constant, the form the firmware itself uses."""
        self._w(0xD2800000 | (value & 0xFFFF) << 5 | rd)
        for i in (1, 2, 3):
            self._w(0xF2800000 | i << 21 | ((value >> 16 * i) & 0xFFFF) << 5 | rd)

    def mov_x(self, rd, rm):
        self._w(0xAA0003E0 | rm << 16 | rd)

    def mov_wr(self, rd, rm):
        self._w(0x2A0003E0 | rm << 16 | rd)

    # ---- arithmetic --------------------------------------------------
    def add_w(self, rd, rn, rm):
        self._w(0x0B000000 | rm << 16 | rn << 5 | rd)

    def sub_w(self, rd, rn, rm):
        self._w(0x4B000000 | rm << 16 | rn << 5 | rd)

    def add_x(self, rd, rn, rm, lsl=0):
        self._w(0x8B000000 | rm << 16 | _imm(lsl, 6) << 10 | rn << 5 | rd)

    def add_xi(self, rd, rn, value):
        self._w(0x91000000 | _imm(value, 12) << 10 | rn << 5 | rd)

    def cmp_wi(self, rn, value):
        self._w(0x7100001F | _imm(value, 12) << 10 | rn << 5)

    def cmp_w(self, rn, rm):
        self._w(0x6B00001F | rm << 16 | rn << 5)

    def and_w3(self, rd, rn):
        """and wD,wN,#3"""
        self._w(0x12000400 | rn << 5 | rd)

    def madd_x(self, rd, rn, rm, ra):
        self._w(0x9B000000 | rm << 16 | ra << 10 | rn << 5 | rd)

    def lsl_wi(self, rd, rn, shift):
        """lsl wD,wN,#shift (ubfm alias)"""
        self._w(0x53000000 | ((32 - shift) % 32) << 16 | (31 - shift) << 10 | rn << 5 | rd)

    # ---- loads and stores -------------------------------------------
    def ldr_x(self, rt, rn, offset=0):
        self._w(0xF9400000 | _imm(offset // 8, 12) << 10 | rn << 5 | rt)

    def str_x(self, rt, rn, offset=0):
        self._w(0xF9000000 | _imm(offset // 8, 12) << 10 | rn << 5 | rt)

    def ldr_w(self, rt, rn, offset=0):
        self._w(0xB9400000 | _imm(offset // 4, 12) << 10 | rn << 5 | rt)

    def str_w(self, rt, rn, offset=0):
        self._w(0xB9000000 | _imm(offset // 4, 12) << 10 | rn << 5 | rt)

    def ldrh_w(self, rt, rn, offset=0):
        self._w(0x79400000 | _imm(offset // 2, 12) << 10 | rn << 5 | rt)

    def strh_w(self, rt, rn, offset=0):
        self._w(0x79000000 | _imm(offset // 2, 12) << 10 | rn << 5 | rt)

    def ldrb_w(self, rt, rn, offset=0):
        self._w(0x39400000 | _imm(offset, 12) << 10 | rn << 5 | rt)

    def strb_w(self, rt, rn, offset=0):
        self._w(0x39000000 | _imm(offset, 12) << 10 | rn << 5 | rt)

    def ldrb_idx(self, rt, rn, rm):
        """ldrb wT,[xN,xM]"""
        self._w(0x38606800 | rm << 16 | rn << 5 | rt)

    def ldr_x_idx8(self, rt, rn, rm):
        """ldr xT,[xN,xM,lsl #3]"""
        self._w(0xF8607800 | rm << 16 | rn << 5 | rt)

    def ldrb_post(self, rt, rn, step):
        """ldrb wT,[xN],#step"""
        self._w(0x38400400 | _imm(step, 9, True) << 12 | rn << 5 | rt)

    def strb_post(self, rt, rn, step):
        """strb wT,[xN],#step"""
        self._w(0x38000400 | _imm(step, 9, True) << 12 | rn << 5 | rt)

    def subs_wi(self, rd, rn, value):
        self._w(0x71000000 | _imm(value, 12) << 10 | rn << 5 | rd)

    def movk_w16(self, rd, value):
        """movk wD,#imm16,lsl #16"""
        self._w(0x72A00000 | _imm(value, 16) << 5 | rd)

    def lsr_wv(self, rd, rn, rm):
        """lsr wD,wN,wM"""
        self._w(0x1AC02400 | rm << 16 | rn << 5 | rd)

    def tbz_w(self, rt, bit, target):
        self._rel(lambda pc: 0x36000000 | _imm(bit, 5) << 19 | _imm((self._target(target) - pc) >> 2, 14, True) << 5 | rt)

    def ldr_w_idx(self, rt, rn, rm):
        """ldr wT,[xN,wM,uxtw #2]"""
        self._w(0xB8605800 | rm << 16 | rn << 5 | rt)

    def stp_pre(self, rt, rt2, offset):
        """stp xT,xT2,[sp,#offset]!"""
        self._w(0xA9800000 | _imm(offset // 8, 7, True) << 15 | rt2 << 10 | 31 << 5 | rt)

    def ldp_post(self, rt, rt2, offset):
        """ldp xT,xT2,[sp],#offset"""
        self._w(0xA8C00000 | _imm(offset // 8, 7, True) << 15 | rt2 << 10 | 31 << 5 | rt)

    def stp(self, rt, rt2, offset):
        self._w(0xA9000000 | _imm(offset // 8, 7, True) << 15 | rt2 << 10 | 31 << 5 | rt)

    def ldp(self, rt, rt2, offset):
        self._w(0xA9400000 | _imm(offset // 8, 7, True) << 15 | rt2 << 10 | 31 << 5 | rt)

    # ---- control flow -----------------------------------------------
    def bl(self, target):
        self._rel(lambda pc: 0x94000000 | _imm((self._target(target) - pc) >> 2, 26, True))

    def b(self, target):
        self._rel(lambda pc: 0x14000000 | _imm((self._target(target) - pc) >> 2, 26, True))

    def b_cond(self, cond, target):
        code = {'eq': 0, 'ne': 1, 'hs': 2, 'lo': 3, 'hi': 8, 'ls': 9, 'ge': 10, 'lt': 11, 'gt': 12, 'le': 13}[cond]
        self._rel(lambda pc: 0x54000000 | _imm((self._target(target) - pc) >> 2, 19, True) << 5 | code)

    def cbz_x(self, rt, target):
        self._rel(lambda pc: 0xB4000000 | _imm((self._target(target) - pc) >> 2, 19, True) << 5 | rt)

    def cbz_w(self, rt, target):
        self._rel(lambda pc: 0x34000000 | _imm((self._target(target) - pc) >> 2, 19, True) << 5 | rt)

    def cbnz_w(self, rt, target):
        self._rel(lambda pc: 0x35000000 | _imm((self._target(target) - pc) >> 2, 19, True) << 5 | rt)

    def adr(self, rd, target):
        def make(pc):
            delta = _imm(self._target(target) - pc, 21, True)
            return 0x10000000 | (delta & 3) << 29 | (delta >> 2) << 5 | rd
        self._rel(make)

    def ret(self):
        self._w(0xD65F03C0)

    def nop(self):
        self._w(0xD503201F)

    def raw(self, word):
        self._w(word)

    # ---- output ------------------------------------------------------
    def words(self):
        return [item if isinstance(item, int) else item[1](item[0]) for item in self.items]

    def bytes(self):
        return b''.join(struct.pack('<I', w) for w in self.words())

    def listing(self, cs):
        """[(va, hex word, text)] from Capstone, for the manifest and for review."""
        out = []
        for i in cs.disasm(self.bytes(), self.va):
            out.append((i.address, i.bytes.hex(), f'{i.mnemonic} {i.op_str}'.strip()))
        if len(out) != len(self.items):
            raise ValueError('Capstone could not decode every emitted word')
        return out
