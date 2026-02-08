"""
Z80命令セット実装パッケージ。
"""
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Operation
from retro_core_tracer.arch.z80.state import Z80CpuState
from .maps import DECODE_MAP, EXECUTE_MAP

# @intent:responsibility 与えられたオペコードをZ80の命令としてデコードします。
# @intent:pre-condition `pc`はデコードするオペコードの先頭アドレスを指している必要があります。
def decode_opcode(opcode: int, bus: Bus, pc: int) -> Operation:
    """
    Z80のオペコードをデコードし、Operationオブジェクトを返します。
    未知のオペコードの場合は"UNKNOWN"を返します。
    """
    decoder = DECODE_MAP.get(opcode)
    if decoder:
        return decoder(opcode, bus, pc)
    return Operation(opcode_hex=f"{opcode:02X}", mnemonic="UNKNOWN", operands=[f"${opcode:02X}"], cycle_count=4, length=1)

# @intent:responsibility デコードされたZ80命令を実行し、CPUの状態を変更します。
# @intent:pre-condition `operation`は有効なOperationオブジェクトである必要があります。
def execute_instruction(operation: Operation, state: Z80CpuState, bus: Bus) -> None:
    """
    デコードされたZ80命令を実行し、CPUの状態を変更します。
    """
    executor = EXECUTE_MAP.get(int(operation.opcode_hex, 16))
    if executor:
        executor(state, bus, operation)
