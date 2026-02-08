# tests/ui/test_code_view_logic.py
"""
CodeViewの更新ロジック（キャッシュとスクロール制御）を検証するテスト。
UIウィジェットですが、QApplicationがあればロジックのテストは可能です。
"""
import pytest
from PySide6.QtWidgets import QApplication, QTableWidget
from PySide6.QtCore import Qt

from retro_core_tracer.ui.code_view import CodeView
from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.z80.cpu import Z80Cpu

# PySide6のテストにはQApplicationのインスタンスが必要
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

class TestCodeViewLogic:
    @pytest.fixture
    def setup_code_view(self, qapp):
        # バックエンドのセットアップ
        bus = Bus()
        ram = RAM(0x10000)
        bus.register_device(0x0000, 0xFFFF, ram)
        
        # テスト用の命令を書き込む
        # 0x1000: NOP
        bus.write(0x1000, 0x00)
        # 0x1001: LD A, 0x55 (2 bytes)
        bus.write(0x1001, 0x3E)
        bus.write(0x1002, 0x55)
        # ...
        # 0x2000: HALT
        bus.write(0x2000, 0x76)

        code_view = CodeView()
        cpu = Z80Cpu(bus)
        code_view.set_cpu(cpu)
        return code_view, bus

    def test_initial_update(self, setup_code_view):
        code_view, bus = setup_code_view
        pc = 0x1000
        
        # 1. 初回の更新
        code_view.update_code(pc)
        
        # データが生成されているか確認
        assert len(code_view.disassembled_data) > 0
        # 最初の行のアドレスがpc (0x1000) であることを確認（簡易実装ではstart_addr=pcのため）
        assert code_view.disassembled_data[0][0] == pc
        
        # テーブルの行数とデータ数が一致するか
        assert code_view.table.rowCount() == len(code_view.disassembled_data)

    def test_update_within_range(self, setup_code_view):
        code_view, bus = setup_code_view
        pc1 = 0x1000
        pc2 = 0x1001 # 次の命令
        
        # 1. 初回の更新 (PC=0x1000)
        code_view.update_code(pc1)
        initial_data_id = id(code_view.disassembled_data) # オブジェクトIDを保存
        
        # 2. 範囲内での更新 (PC=0x1001)
        code_view.update_code(pc2)
        
        # データが再生成されていない（キャッシュが効いている）ことを確認
        assert id(code_view.disassembled_data) == initial_data_id
        
        # ハイライトが移動しているか確認 (背景色チェックは難しいので、ロジック上の分岐を通ったことをデータ不変で確認)

    def test_update_out_of_range(self, setup_code_view):
        code_view, bus = setup_code_view
        pc1 = 0x1000
        pc_far = 0x2000 # 遠くのアドレス
        
        # 1. 初回の更新 (PC=0x1000)
        code_view.update_code(pc1)
        initial_data_id = id(code_view.disassembled_data)
        
        # 2. 範囲外への更新 (PC=0x2000)
        # 0x2000は0x1000からの128バイト範囲には含まれないはず
        code_view.update_code(pc_far)
        
        # データが再生成されていることを確認
        assert id(code_view.disassembled_data) != initial_data_id
        
        # 新しいデータの先頭付近が0x2000であることを確認
        # (ロジック上、見つからなければ start_addr=pc_far で再生成するはず)
        found = False
        for addr, _, _ in code_view.disassembled_data:
            if addr == pc_far:
                found = True
                break
        assert found
