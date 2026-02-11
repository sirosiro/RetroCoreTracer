import unittest
from retro_core_tracer.config.loader import ConfigLoader
from retro_core_tracer.config.builder import SystemBuilder
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mc6800.cpu import Mc6800Cpu

class TestMc6800ResetVector(unittest.TestCase):
    def test_reset_vector_loading(self):
        # 1. YAML設定のシミュレーション
        yaml_content = """
architecture: "MC6800"
memory_map:
  - start: 0x0000
    end: 0x7FFF
    type: "RAM"
  - start: 0x8000
    end: 0xFFFF
    type: "ROM"
initial_state:
  use_reset_vector: true
"""
        import yaml
        data = yaml.safe_load(yaml_content)
        loader = ConfigLoader()
        config = loader._parse_config(data)
        
        # 2. システム構築
        builder = SystemBuilder()
        cpu, bus = builder.build_system(config)
        
        # 3. バスにリセットベクトルを書き込む (ROMへのロードをシミュレート)
        # $FFFE -> $80, $FFFF -> $12  => $8012
        bus.write(0xFFFE, 0x80)
        bus.write(0xFFFF, 0x12)
        
        # 4. CPUをリセット (実機でのリセットボタン押下をシミュレート)
        cpu.reset()
        
        # 5. PCがベクトルから読み込まれているか確認
        self.assertEqual(cpu.get_state().pc, 0x8012)

if __name__ == '__main__':
    unittest.main()
