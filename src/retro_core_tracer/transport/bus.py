# retro_core_tracer/transport/bus.py
"""
Transport Layer (共通バス)

このモジュールは、システム全体のメモリアドレス空間を抽象化し、
読み書きアクセスを適切なデバイスに委譲する責務を負います。
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict
from dataclasses import dataclass, field
from enum import Enum

# @intent:responsibility バスアクセスを記録するためのタイプを定義します。
class BusAccessType(Enum):
    READ = "READ"
    WRITE = "WRITE"

# @intent:responsibility 個々のバスアクセス操作を記録します。
@dataclass(frozen=True) # 不変データ構造
class BusAccess:
    """
    バス上で行われた単一のアクセス（読み込みまたは書き込み）を記録するデータクラス。
    """
    address: int
    data: int # 8bit value
    access_type: BusAccessType

# @intent:responsibility バスの抽象デバイスインターフェースを定義します。
class Device(ABC):
    """
    バスに接続されるデバイスの抽象基底クラス。
    全てのデバイスはreadとwriteのインターフェースを実装する必要があります。
    """
    # @intent:responsibility 指定されたアドレスから8bitのデータを読み出す責務を負います。
    # @intent:pre-condition アドレスはデバイスの有効範囲内である必要があります。
    @abstractmethod
    def read(self, address: int) -> int:
        """
        指定されたアドレスから8bitのデータを読み出します。
        アドレスはデバイス内でのオフセットとして扱われます。
        """
        pass

    # @intent:responsibility 指定されたアドレスに8bitのデータを書き込む責務を負います。
    # @intent:pre-condition アドレスはデバイスの有効範囲内であり、データは8bit値である必要があります。
    @abstractmethod
    def write(self, address: int, data: int) -> None:
        """
        指定されたアドレスに8bitのデータを書き込みます。
        アドレスはデバイス内でのオフセットとして扱われます。
        """
        pass

# @intent:responsibility 基本的なRAMデバイスの機能を提供します。
class RAM(Device):
    """
    テストおよび基本的なメモリ操作のためのRAMデバイス。
    """
    # @intent:responsibility 指定されたサイズのメモリ領域を初期化します。
    # @intent:pre-condition sizeは正の整数である必要があります。
    def __init__(self, size: int):
        if not isinstance(size, int) or size <= 0:
            raise ValueError("RAM size must be a positive integer.")
        self._memory = bytearray(size)
        self._size = size

    # @intent:responsibility 指定されたアドレスから8bitのデータを読み出します。
    # @intent:pre-condition アドレスはRAMの有効範囲内である必要があります。
    def read(self, address: int) -> int:
        if not 0 <= address < self._size:
            raise IndexError(f"Address {address} out of bounds for RAM of size {self._size}.")
        return self._memory[address]

    # @intent:responsibility 指定されたアドレスに8bitのデータを書き込みます。
    # @intent:pre-condition アドレスはRAMの有効範囲内であり、データは8bit値である必要があります。
    def write(self, address: int, data: int) -> None:
        if not 0 <= address < self._size:
            raise IndexError(f"Address {address} out of bounds for RAM of size {self._size}.")
        if not 0 <= data <= 0xFF:
            raise ValueError(f"Data {data} is not an 8-bit value.")
        self._memory[address] = data

    # @intent:responsibility RAMのサイズを返します。
    def get_size(self) -> int:
        return self._size

# @intent:responsibility メモリアドレス空間を管理し、デバイスへのアクセスをディスパッチする共通バス。
# @intent:rationale バスの全てのアクセスを記録し、Snapshotに含めることでシステムの観測可能性を高めます。
class Bus:
    """
    メモリアドレス空間を管理し、デバイスへのアクセスをディスパッチする共通バス。
    バス上で行われた全てのメモリ/IOアクセスを記録する機能を提供します。
    """
    # @intent:responsibility 空のメモリマップとバスアクティビティログを初期化します。
    def __init__(self):
        # メモリマップ: (start_address, end_address, device) のタプルリスト
        self._memory_map: List[Tuple[int, int, Device]] = []
        self._bus_activity_log: List[BusAccess] = [] # バスアクセスログ

    # @intent:responsibility バスアクセスをログに記録します。
    def _log_access(self, address: int, data: int, access_type: BusAccessType) -> None:
        """
        バスアクセス操作を内部ログに追加します。
        """
        self._bus_activity_log.append(BusAccess(address=address, data=data, access_type=access_type))

    # @intent:responsibility 記録されたバスアクティビティログを取得し、クリアします。
    def get_and_clear_activity_log(self) -> List[BusAccess]:
        """
        現在のバスアクティビティログを返し、内部ログをクリアします。
        """
        log = self._bus_activity_log
        self._bus_activity_log = [] # ログをクリア
        return log

    # @intent:responsibility 指定されたアドレス範囲にデバイスを登録します。
    # @intent:pre-condition start_address <= end_addressかつ非負であり、deviceはDeviceのインスタンスである必要があります。
    # @intent:rationale アドレス範囲の重複チェックは行いません。これはBusの責務ではなく、システム設計の層で管理されるべきと判断しました。
    #                 もしRAMデバイスを登録する場合、そのサイズが指定されたアドレス範囲と一致する必要があります。
    def register_device(self, start_address: int, end_address: int, device: Device) -> None:
        """
        指定されたアドレス範囲にデバイスを登録します。
        アドレス範囲の重複チェックは行いません。呼び出し元が責任を持ちます。
        """
        if not (0 <= start_address <= end_address):
            raise ValueError("Invalid address range: start_address must be <= end_address and non-negative.")
        if not isinstance(device, Device):
            raise TypeError("Device must be an instance of a class derived from Device.")

        # デバイスのサイズチェック (もしRAMなどの固定サイズデバイスの場合)
        if isinstance(device, RAM):
            expected_size = end_address - start_address + 1
            if device.get_size() != expected_size:
                raise ValueError(
                    f"Registered RAM device size ({device.get_size()} bytes) does not match "
                    f"the specified address range size ({expected_size} bytes)."
                )

        self._memory_map.append((start_address, end_address, device))
        # 登録順序に依存しないように、アドレスでソートすることも考慮できるが、
        # 現在は単純にリストに追加する。より複雑なアドレス解決が必要になったら検討する。
        # self._memory_map.sort(key=lambda x: x[0])

    # @intent:responsibility 指定されたアドレスに対応するデバイスとオフセットを検索します。
    # @intent:post-condition デバイスが見つからなかった場合、IndexErrorを発生させます。
    def _find_device(self, address: int) -> Tuple[Device, int]:
        """
        指定されたアドレスに対応するデバイスと、デバイス内でのオフセットを検索します。
        見つからない場合はIndexErrorを発生させます。
        """
        for start, end, device in self._memory_map:
            if start <= address <= end:
                return device, address - start
        raise IndexError(f"Address {address:#06x} not mapped to any device.")

    # @intent:responsibility 指定されたアドレスから8bitのデータを読み出します。
    # @intent:pre-condition アドレスはマップされたデバイスの有効範囲内である必要があります。
    def read(self, address: int) -> int:
        """
        指定されたアドレスから8bitのデータを読み出します。
        """
        device, offset = self._find_device(address)
        data = device.read(offset)
        self._log_access(address, data, BusAccessType.READ)
        return data

    # @intent:responsibility 指定されたアドレスに8bitのデータを書き込みます。
    # @intent:pre-condition アドレスはマップされたデバイスの有効範囲内であり、データは8bit値である必要があります。
    def write(self, address: int, data: int) -> None:
        """
        指定されたアドレスに8bitのデータを書き込みます。
        """
        device, offset = self._find_device(address)
        device.write(offset, data)
        self._log_access(address, data, BusAccessType.WRITE)

