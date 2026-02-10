# src/retro_core_tracer/arch/mc6800/instructions/__init__.py
"""
MC6800命令セット実装パッケージ。
"""
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Operation
from retro_core_tracer.arch.mc6800.state import Mc6800CpuState
from .maps import DECODE_MAP, EXECUTE_MAP

# @intent:responsibility MC6800のオペコードをデコードします。
def decode_opcode(opcode: int, bus: Bus, pc: int) -> Operation:
    """
    MC6800のオペコードをデコードし、Operationオブジェクトを返します。
    """
    decoder = DECODE_MAP.get(opcode)
    if decoder:
        return decoder(opcode, bus, pc)
    return Operation(opcode_hex=f"{opcode:02X}", mnemonic="UNKNOWN", operands=[f"${opcode:02X}"], cycle_count=2, length=1)

# @intent:responsibility デコードされたMC6800命令を実行します。
def execute_instruction(operation: Operation, state: Mc6800CpuState, bus: Bus) -> None:
    """
    デコードされたMC6800命令を実行し、CPUの状態を変更します。
    """
    executor = EXECUTE_MAP.get(int(operation.opcode_hex, 16))
    if executor:
        executor(state, bus, operation)