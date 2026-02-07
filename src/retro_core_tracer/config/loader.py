import yaml
from typing import Dict, Any
from .models import SystemConfig, MemoryRegion, CpuInitialState

class ConfigLoader:
    def load_from_file(self, path: str) -> SystemConfig:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return self._parse_config(data)

    def _parse_config(self, data: Dict[str, Any]) -> SystemConfig:
        arch = data.get("architecture", "Z80")
        
        # Parse Memory Map
        memory_map = []
        for region_data in data.get("memory_map", []):
            start = self._parse_int(region_data.get("start"))
            end = self._parse_int(region_data.get("end"))
            rtype = region_data.get("type", "RAM")
            label = region_data.get("label", "")
            permissions = region_data.get("permissions", "RW")
            
            memory_map.append(MemoryRegion(
                start=start,
                end=end,
                type=rtype,
                label=label,
                permissions=permissions
            ))
            
        # Parse Initial State
        initial_state_data = data.get("initial_state", {})
        initial_state = CpuInitialState(
            pc=self._parse_int(initial_state_data.get("pc", 0)),
            sp=self._parse_int(initial_state_data.get("sp", 0)),
            registers=initial_state_data.get("registers", {})
        )
            
        return SystemConfig(
            architecture=arch, 
            memory_map=memory_map,
            initial_state=initial_state
        )

    def _parse_int(self, value: Any) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            if value.startswith("0x"):
                return int(value, 16)
            return int(value)
        raise ValueError(f"Invalid integer format: {value}")
