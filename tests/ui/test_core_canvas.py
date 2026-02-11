import sys
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor
from retro_core_tracer.ui.core_canvas import CoreCanvas
from retro_core_tracer.core.snapshot import Snapshot, BusAccess, BusAccessType, Operation, Metadata
from retro_core_tracer.core.state import CpuState
from retro_core_tracer.config.models import SystemConfig, MemoryRegion, IoRegion

# ダミーデータ
class DummyState(CpuState):
    pass

class TestCoreCanvas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_init(self):
        canvas = CoreCanvas()
        self.assertIsNotNone(canvas.scene)

    def test_memory_labels_with_address(self):
        """
        十分な幅があるメモリ領域にアドレス範囲を含むラベルが表示されることを検証します。
        """
        canvas = CoreCanvas()
        # 0x0000 - 0x7FFF (32KB) の広い領域を作成
        config = SystemConfig(
            architecture="Z80",
            memory_map=[
                MemoryRegion(0x0000, 0x7FFF, "ROM", "OS"),
            ]
        )
        canvas.set_config(config)
        
        items = canvas.scene.items()
        label_found = False
        expected_label = "ROM (0x0000-0x7FFF)"
        for item in items:
            if hasattr(item, "text") and expected_label in item.text():
                label_found = True
                break
        self.assertTrue(label_found, f"Memory label '{expected_label}' should be visible for 32KB region")

    def test_mc6800_io_visibility(self):
        canvas = CoreCanvas()
        config = SystemConfig(architecture="MC6800")
        canvas.set_config(config)
        
        items = canvas.scene.items()
        io_title_found = False
        for item in items:
            if hasattr(item, "text") and "I/O Ports" in item.text():
                io_title_found = True
                break
        self.assertFalse(io_title_found, "I/O Ports block should NOT be visible for MC6800")

if __name__ == '__main__':
    unittest.main()
