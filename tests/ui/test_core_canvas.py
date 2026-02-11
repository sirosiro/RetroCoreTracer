import sys
import unittest
from PySide6.QtWidgets import QApplication
from retro_core_tracer.ui.core_canvas import CoreCanvas
from retro_core_tracer.core.snapshot import Snapshot, BusAccess, BusAccessType, Operation, Metadata
from retro_core_tracer.core.state import CpuState

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

    def test_update_view(self):
        canvas = CoreCanvas()
        
        # ダミースナップショット作成
        access = BusAccess(0x1234, 0xFF, BusAccessType.READ)
        snapshot = Snapshot(
            state=DummyState(0, 0),
            operation=Operation("00", "NOP", [], [], 4, 1),
            bus_activity=[access],
            metadata=Metadata(0, "")
        )
        
        canvas.update_view(snapshot)
        
        # private メンバへのアクセスだが、テストのため許容
        self.assertEqual(len(canvas._animation_queue), 1)
        self.assertEqual(canvas._animation_queue[0], access)

if __name__ == '__main__':
    unittest.main()
