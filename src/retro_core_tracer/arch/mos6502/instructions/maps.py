# src/retro_core_tracer/arch/mos6502/instructions/maps.py
"""
MOS 6502 命令マップとデコード/実行ロジック。
"""
from typing import Callable, Dict, Tuple, Any

from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Operation
from retro_core_tracer.arch.mos6502.state import Mos6502CpuState
from retro_core_tracer.arch.mos6502.instructions import base, load, alu, control

# Addressing Mode Function Type
AddrFunc = Callable[[int, Bus, Mos6502CpuState], base.AddressingResult]
# Execution Function Type
ExecFunc = Callable[[Mos6502CpuState, Bus, base.AddressingResult], Mos6502CpuState]

# Opcode Entry: (Mnemonic, Addressing Mode, Execution Function, Base Cycles)
OpcodeEntry = Tuple[str, AddrFunc, ExecFunc, int]

OPCODE_MAP: Dict[int, OpcodeEntry] = {
    # --- Load/Store/Transfer (Already Implemented) ---
    0xA9: ("LDA", base.addr_immediate, load.lda, 2),
    0xA5: ("LDA", base.addr_zeropage, load.lda, 3),
    0xB5: ("LDA", base.addr_zeropage_x, load.lda, 4),
    0xAD: ("LDA", base.addr_absolute, load.lda, 4),
    0xBD: ("LDA", base.addr_absolute_x, load.lda, 4),
    0xB9: ("LDA", base.addr_absolute_y, load.lda, 4),
    0xA1: ("LDA", base.addr_indexed_indirect, load.lda, 6),
    0xB1: ("LDA", base.addr_indirect_indexed, load.lda, 5),

    0xA2: ("LDX", base.addr_immediate, load.ldx, 2),
    0xA6: ("LDX", base.addr_zeropage, load.ldx, 3),
    0xB6: ("LDX", base.addr_zeropage_y, load.ldx, 4),
    0xAE: ("LDX", base.addr_absolute, load.ldx, 4),
    0xBE: ("LDX", base.addr_absolute_y, load.ldx, 4),

    0xA0: ("LDY", base.addr_immediate, load.ldy, 2),
    0xA4: ("LDY", base.addr_zeropage, load.ldy, 3),
    0xB4: ("LDY", base.addr_zeropage_x, load.ldy, 4),
    0xAC: ("LDY", base.addr_absolute, load.ldy, 4),
    0xBC: ("LDY", base.addr_absolute_x, load.ldy, 4),

    0x85: ("STA", base.addr_zeropage, load.sta, 3),
    0x95: ("STA", base.addr_zeropage_x, load.sta, 4),
    0x8D: ("STA", base.addr_absolute, load.sta, 4),
    0x9D: ("STA", base.addr_absolute_x, load.sta, 5),
    0x99: ("STA", base.addr_absolute_y, load.sta, 5),
    0x81: ("STA", base.addr_indexed_indirect, load.sta, 6),
    0x91: ("STA", base.addr_indirect_indexed, load.sta, 6),

    0x86: ("STX", base.addr_zeropage, load.stx, 3),
    0x96: ("STX", base.addr_zeropage_y, load.stx, 4),
    0x8E: ("STX", base.addr_absolute, load.stx, 4),

    0x84: ("STY", base.addr_zeropage, load.sty, 3),
    0x94: ("STY", base.addr_zeropage_x, load.sty, 4),
    0x8C: ("STY", base.addr_absolute, load.sty, 4),

    0xAA: ("TAX", base.addr_implied, load.tax, 2),
    0xA8: ("TAY", base.addr_implied, load.tay, 2),
    0x8A: ("TXA", base.addr_implied, load.txa, 2),
    0x98: ("TYA", base.addr_implied, load.tya, 2),
    0x9A: ("TXS", base.addr_implied, load.txs, 2),
    0xBA: ("TSX", base.addr_implied, load.tsx, 2),

    # --- ALU Operations ---
    # ADC
    0x69: ("ADC", base.addr_immediate, alu.adc, 2),
    0x65: ("ADC", base.addr_zeropage, alu.adc, 3),
    0x75: ("ADC", base.addr_zeropage_x, alu.adc, 4),
    0x6D: ("ADC", base.addr_absolute, alu.adc, 4),
    0x7D: ("ADC", base.addr_absolute_x, alu.adc, 4),
    0x79: ("ADC", base.addr_absolute_y, alu.adc, 4),
    0x61: ("ADC", base.addr_indexed_indirect, alu.adc, 6),
    0x71: ("ADC", base.addr_indirect_indexed, alu.adc, 5),

    # SBC
    0xE9: ("SBC", base.addr_immediate, alu.sbc, 2),
    0xE5: ("SBC", base.addr_zeropage, alu.sbc, 3),
    0xF5: ("SBC", base.addr_zeropage_x, alu.sbc, 4),
    0xED: ("SBC", base.addr_absolute, alu.sbc, 4),
    0xFD: ("SBC", base.addr_absolute_x, alu.sbc, 4),
    0xF9: ("SBC", base.addr_absolute_y, alu.sbc, 4),
    0xE1: ("SBC", base.addr_indexed_indirect, alu.sbc, 6),
    0xF1: ("SBC", base.addr_indirect_indexed, alu.sbc, 5),

    # CMP
    0xC9: ("CMP", base.addr_immediate, alu.cmp, 2),
    0xC5: ("CMP", base.addr_zeropage, alu.cmp, 3),
    0xD5: ("CMP", base.addr_zeropage_x, alu.cmp, 4),
    0xCD: ("CMP", base.addr_absolute, alu.cmp, 4),
    0xDD: ("CMP", base.addr_absolute_x, alu.cmp, 4),
    0xD9: ("CMP", base.addr_absolute_y, alu.cmp, 4),
    0xC1: ("CMP", base.addr_indexed_indirect, alu.cmp, 6),
    0xD1: ("CMP", base.addr_indirect_indexed, alu.cmp, 5),

    # CPX
    0xE0: ("CPX", base.addr_immediate, alu.cpx, 2),
    0xE4: ("CPX", base.addr_zeropage, alu.cpx, 3),
    0xEC: ("CPX", base.addr_absolute, alu.cpx, 4),

    # CPY
    0xC0: ("CPY", base.addr_immediate, alu.cpy, 2),
    0xC4: ("CPY", base.addr_zeropage, alu.cpy, 3),
    0xCC: ("CPY", base.addr_absolute, alu.cpy, 4),

    # AND
    0x29: ("AND", base.addr_immediate, alu.and_, 2),
    0x25: ("AND", base.addr_zeropage, alu.and_, 3),
    0x35: ("AND", base.addr_zeropage_x, alu.and_, 4),
    0x2D: ("AND", base.addr_absolute, alu.and_, 4),
    0x3D: ("AND", base.addr_absolute_x, alu.and_, 4),
    0x39: ("AND", base.addr_absolute_y, alu.and_, 4),
    0x21: ("AND", base.addr_indexed_indirect, alu.and_, 6),
    0x31: ("AND", base.addr_indirect_indexed, alu.and_, 5),

    # ORA
    0x09: ("ORA", base.addr_immediate, alu.ora, 2),
    0x05: ("ORA", base.addr_zeropage, alu.ora, 3),
    0x15: ("ORA", base.addr_zeropage_x, alu.ora, 4),
    0x0D: ("ORA", base.addr_absolute, alu.ora, 4),
    0x1D: ("ORA", base.addr_absolute_x, alu.ora, 4),
    0x19: ("ORA", base.addr_absolute_y, alu.ora, 4),
    0x01: ("ORA", base.addr_indexed_indirect, alu.ora, 6),
    0x11: ("ORA", base.addr_indirect_indexed, alu.ora, 5),

    # EOR
    0x49: ("EOR", base.addr_immediate, alu.eor, 2),
    0x45: ("EOR", base.addr_zeropage, alu.eor, 3),
    0x55: ("EOR", base.addr_zeropage_x, alu.eor, 4),
    0x4D: ("EOR", base.addr_absolute, alu.eor, 4),
    0x5D: ("EOR", base.addr_absolute_x, alu.eor, 4),
    0x59: ("EOR", base.addr_absolute_y, alu.eor, 4),
    0x41: ("EOR", base.addr_indexed_indirect, alu.eor, 6),
    0x51: ("EOR", base.addr_indirect_indexed, alu.eor, 5),

    # BIT
    0x24: ("BIT", base.addr_zeropage, alu.bit, 3),
    0x2C: ("BIT", base.addr_absolute, alu.bit, 4),

    # Shift / Rotate
    0x0A: ("ASL", base.addr_implied, alu.asl, 2), # Accumulator
    0x06: ("ASL", base.addr_zeropage, alu.asl, 5),
    0x16: ("ASL", base.addr_zeropage_x, alu.asl, 6),
    0x0E: ("ASL", base.addr_absolute, alu.asl, 6),
    0x1E: ("ASL", base.addr_absolute_x, alu.asl, 7),

    0x4A: ("LSR", base.addr_implied, alu.lsr, 2),
    0x46: ("LSR", base.addr_zeropage, alu.lsr, 5),
    0x56: ("LSR", base.addr_zeropage_x, alu.lsr, 6),
    0x4E: ("LSR", base.addr_absolute, alu.lsr, 6),
    0x5E: ("LSR", base.addr_absolute_x, alu.lsr, 7),

    0x2A: ("ROL", base.addr_implied, alu.rol, 2),
    0x26: ("ROL", base.addr_zeropage, alu.rol, 5),
    0x36: ("ROL", base.addr_zeropage_x, alu.rol, 6),
    0x2E: ("ROL", base.addr_absolute, alu.rol, 6),
    0x3E: ("ROL", base.addr_absolute_x, alu.rol, 7),

    0x6A: ("ROR", base.addr_implied, alu.ror, 2),
    0x66: ("ROR", base.addr_zeropage, alu.ror, 5),
    0x76: ("ROR", base.addr_zeropage_x, alu.ror, 6),
    0x6E: ("ROR", base.addr_absolute, alu.ror, 6),
    0x7E: ("ROR", base.addr_absolute_x, alu.ror, 7),

    # INC/DEC
    0xE6: ("INC", base.addr_zeropage, alu.inc, 5),
    0xF6: ("INC", base.addr_zeropage_x, alu.inc, 6),
    0xEE: ("INC", base.addr_absolute, alu.inc, 6),
    0xFE: ("INC", base.addr_absolute_x, alu.inc, 7),

    0xC6: ("DEC", base.addr_zeropage, alu.dec, 5),
    0xD6: ("DEC", base.addr_zeropage_x, alu.dec, 6),
    0xCE: ("DEC", base.addr_absolute, alu.dec, 6),
    0xDE: ("DEC", base.addr_absolute_x, alu.dec, 7),

    0xE8: ("INX", base.addr_implied, alu.inx, 2),
    0xCA: ("DEX", base.addr_implied, alu.dex, 2),
    0xC8: ("INY", base.addr_implied, alu.iny, 2),
    0x88: ("DEY", base.addr_implied, alu.dey, 2),

    # --- Control Instructions ---
    # Branch
    0x90: ("BCC", base.addr_relative, control.bcc, 2), # +1 if branch taken, +2 if page crossed
    0xB0: ("BCS", base.addr_relative, control.bcs, 2),
    0xF0: ("BEQ", base.addr_relative, control.beq, 2),
    0xD0: ("BNE", base.addr_relative, control.bne, 2),
    0x30: ("BMI", base.addr_relative, control.bmi, 2),
    0x10: ("BPL", base.addr_relative, control.bpl, 2),
    0x50: ("BVC", base.addr_relative, control.bvc, 2),
    0x70: ("BVS", base.addr_relative, control.bvs, 2),

    # Jump / Subroutine
    0x4C: ("JMP", base.addr_absolute, control.jmp, 3),
    0x6C: ("JMP", base.addr_indirect, control.jmp, 5),
    0x20: ("JSR", base.addr_absolute, control.jsr, 6),
    0x60: ("RTS", base.addr_implied, control.rts, 6),

    # Stack
    0x48: ("PHA", base.addr_implied, control.pha, 3),
    0x08: ("PHP", base.addr_implied, control.php, 3),
    0x68: ("PLA", base.addr_implied, control.pla, 4),
    0x28: ("PLP", base.addr_implied, control.plp, 4),

    # Flags
    0x18: ("CLC", base.addr_implied, control.clc, 2),
    0x38: ("SEC", base.addr_implied, control.sec, 2),
    0x58: ("CLI", base.addr_implied, control.cli, 2),
    0x78: ("SEI", base.addr_implied, control.sei, 2),
    0xB8: ("CLV", base.addr_implied, control.clv, 2),
    0xD8: ("CLD", base.addr_implied, control.cld, 2),
    0xF8: ("SED", base.addr_implied, control.sed, 2),

    # System
    0xEA: ("NOP", base.addr_implied, control.nop, 2),
    0x00: ("BRK", base.addr_implied, control.brk, 7),
    0x40: ("RTI", base.addr_implied, control.rti, 6),
}

def decode_opcode(opcode: int, bus: Bus, pc: int, state: Mos6502CpuState) -> Operation:
    entry = OPCODE_MAP.get(opcode)
    if not entry:
        return Operation(f"{opcode:02X}", "???", [], [], 0, 1)
    
    mnemonic, addr_func, _, base_cycles = entry
    
    _, _, extra_cycles, op_str, op_bytes = addr_func(pc, bus, state)
    
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=mnemonic,
        operands=[op_str] if op_str else [],
        operand_bytes=op_bytes,
        cycle_count=base_cycles + extra_cycles,
        length=1 + len(op_bytes)
    )

def execute_instruction(operation: Operation, state: Mos6502CpuState, bus: Bus) -> Mos6502CpuState:
    opcode = int(operation.opcode_hex, 16)
    entry = OPCODE_MAP.get(opcode)
    if not entry:
        return state
        
    _, addr_func, exec_func, _ = entry
    
    # Execute phase addressing resolution
    addr_res = addr_func(state.pc, bus, state)
    
    return exec_func(state, bus, addr_res)