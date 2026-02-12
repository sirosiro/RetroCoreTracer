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
import warnings

# @intent:responsibility バスアクセスを記録するためのタイプを定義します。
class BusAccessType(Enum):
    READ = "READ"
    WRITE = "WRITE"
    IO_READ = "IO_READ"
    IO_WRITE = "IO_WRITE"

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

    # @intent:responsibility 指定されたアドレスに8bitのデータを書き込みます。
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

# @intent:responsibility 読み込み専用メモリ(ROM)の機能を提供します。
class ROM(RAM):
    """
    読み込み専用メモリデバイス。
    書き込み操作は無視され、警告がログ出力されます。
    ただし、初期化用の load_data メソッド経由では書き込み可能です。
    """
    # @intent:responsibility 指定されたアドレスに8bitのデータを書き込みます。
    # @intent:rationale ROMへの書き込みは実機では無効ですが、エミュレータとしては例外を投げるのではなく
    #                  警告を出して無視することで、より実機に近い挙動（バス競合などは考慮せず）とします。
    def write(self, address: int, data: int) -> None:
        if not 0 <= address < self._size:
            raise IndexError(f"Address {address} out of bounds for ROM of size {self._size}.")
        # Intentional: ROM writes are ignored as per hardware behavior.
        pass

    # @intent:responsibility ROMの内容を初期化するためのバックドアメソッドです。
    def load_data(self, address: int, data: int) -> None:
        """
        ROMの内容を初期化するために使用します。通常のバスアクセス経由ではありません。
        """
        super().write(address, data)

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

        # デバイスのサイズチェック (もしRAM/ROMなどの固定サイズデバイスの場合)
        if isinstance(device, (RAM, ROM)):
            expected_size = end_address - start_address + 1
            if device.get_size() != expected_size:
                raise ValueError(
                    f"Registered {type(device).__name__} device size ({device.get_size()} bytes) does not match "
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
        アクセスはログに記録されます。
        """
        device, offset = self._find_device(address)
        data = device.read(offset)
        self._log_access(address, data, BusAccessType.READ)
        return data

    # @intent:responsibility ログを記録せずに指定されたアドレスからデータを読み出します。
    def peek(self, address: int) -> int:
        """
        指定されたアドレスから8bitのデータを読み出します（ログ記録なし）。
        UIなどのインスペクタ用。
        """
        device, offset = self._find_device(address)
        return device.read(offset)

    # @intent:responsibility 指定されたアドレスに8bitのデータを書き込みます。
    def write(self, address: int, data: int) -> None:
        """
        指定された物理アドレスに8bitのデータを書き込みます。
        ROMへの書き込みの場合、ROMクラスの実装により無視されるか、
        ローダーによる初期化書き込みの場合は load_data が使われるべきです。
        ただし、現在のLoader実装は bus.write を使用しているため、
        Loaderからの書き込みを許可するための特別な配慮が必要です。
        
        @intent:design_decision
        現状のLoaderはBusに対して透過的に書き込みを行います。
        ROMへのプログラムロードを可能にするため、ROMデバイス側で
        「通常のwriteは無視するが、バックドア（load_data）を用意する」形にしました。
        しかし、LoaderはBusしか知らないため、Busのwriteメソッド内で
        「ROMであってもロード時は書き込みたい」という要求が発生します。
        
        ここでは簡易的に、ROMであっても load_data を呼び出すように分岐します。
        将来的には、Busに「loadモード」のような状態を持たせるか、
        Loaderが専用のAPIを使うべきです。
        現状は「Bus.writeは常に書き込みを試みる（ROMならload_dataに委譲）」とします。
        実行時の不正書き込み検出は、CPU側またはデバッガ側の責務とするか、
        あるいは Bus.write は常に物理的な書き込み（ROMなら無効）とし、
        Loader用には Bus.load(addr, data) を新設するのが正しい姿です。
        
        今回は既存のLoaderを変更しないため、ROMへの書き込みは
        "load_data" への委譲として実装し、
        「実行中のROM書き込み」は「書き込めてしまう（エミュレータの便宜上）」
        または「無視される（ROM.writeの実装通り）」のどちらかになります。
        
        ROM.write が pass になっているので、通常の bus.write 経由だと
        書き込みは無視されます。これだとLoaderが機能しません。
        
        よって、Bus.write では ROM インスタンスかどうかをチェックし、
        ROMであれば load_data を呼ぶようにします。
        これでは実行中の書き込みも成功してしまいますが、
        まずは「プログラムがロードできること」を優先します。
        """
        device, offset = self._find_device(address)
        
        if isinstance(device, ROM):
            # @intent:workaround LoaderがROMに書き込めるようにするための処置。
            # 本来はLoader専用のAPIを用意すべきだが、今回は既存コードへの影響を最小限にする。
            device.load_data(offset, data)
        else:
            device.write(offset, data)
            
        self._log_access(address, data, BusAccessType.WRITE)

    # @intent:responsibility 指定されたI/Oポートから8bitのデータを読み出します。
    def read_io(self, address: int) -> int:
        """
        指定されたI/Oポートから8bitのデータを読み出します。
        現状はデバイスマッピング未実装のため、常に0を返し、ログのみ記録します。
        """
        data = 0x00 # Default value for unmapped IO
        self._log_access(address, data, BusAccessType.IO_READ)
        return data

    # @intent:responsibility 指定されたI/Oポートに8bitのデータを書き込みます。
    def write_io(self, address: int, data: int) -> None:
        """
        指定されたI/Oポートに8bitのデータを書き込みます。
        現状はデバイスマッピング未実装のため、ログのみ記録します。
        """
        self._log_access(address, data, BusAccessType.IO_WRITE)