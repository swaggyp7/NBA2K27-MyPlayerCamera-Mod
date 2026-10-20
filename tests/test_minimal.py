"""In-memory lifecycle test: proves code bytes stay untouched and restore is exact."""
import builtins
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import myplayer_camera_minimal as mod


class FakeMemory:
    def __init__(self, base, flag):
        self.base = base
        self.data = {}
        self.writes = []
        self.closed = False
        self.alloc = 0x700000000000
        for rva, signature in mod.CODE_SIGNATURES.items():
            self.seed(base + rva, signature)
        self.seed(base + mod.LIST_RVA, struct.pack("<14I", *mod.BASELINE))
        for rva in mod.DESC_RVAS:
            self.seed(base + rva, struct.pack("<QI", base + mod.LIST_RVA, 14))
        self.seed(base + mod.FLAG_RVA, bytes([flag]))
        self.seed(base + mod.ACTIVE_RVA, struct.pack("<ii", 1, 1))

    def seed(self, address, blob):
        self.data.update({address + offset: byte for offset, byte in enumerate(blob)})

    def read(self, address, size):
        return bytes(self.data[address + offset] for offset in range(size))

    def write(self, address, blob):
        for rva, signature in mod.CODE_SIGNATURES.items():
            assert not (address < self.base + rva + len(signature) and address + len(blob) > self.base + rva)
        self.writes.append((address, blob))
        self.seed(address, blob)

    def allocate_list(self, blob):
        self.write(self.alloc, blob)
        return self.alloc

    def alive(self):
        return True

    def close(self):
        self.closed = True


class MinimalTests(unittest.TestCase):
    def run_case(self, flag):
        base = 0x140000000
        memory = FakeMemory(base, flag)
        original = dict(memory.data)
        class FakeK:
            @staticmethod
            def VirtualFreeEx(handle, address, size, kind):
                assert address == memory.alloc
                return True
        memory.handle = object()
        def check_installed(prompt):
            self.assertTrue(all(memory.read(base + rva, 12) == struct.pack("<QI", memory.alloc, 15) for rva in mod.DESC_RVAS))
            self.assertEqual(memory.read(base + mod.FLAG_RVA, 1), b"\x01")
            return ""
        with patch.object(mod, "find_game", return_value=(1234, base)), \
             patch.object(mod, "GameMemory", return_value=memory), \
             patch.object(mod, "K", FakeK()), \
             patch.object(builtins, "input", check_installed):
            mod.run()
        self.assertTrue(memory.closed)
        for address, byte in original.items():
            self.assertEqual(memory.data[address], byte, hex(address))
        self.assertEqual(len(mod.DESC_RVAS), 10)

    def test_flag_zero(self):
        self.run_case(0)

    def test_flag_one(self):
        self.run_case(1)

    def test_old_hook_rejected_without_writes(self):
        base = 0x140000000
        memory = FakeMemory(base, 0)
        memory.seed(base + 0xc2d000, b"\xe9")
        with self.assertRaisesRegex(RuntimeError, "旧版代码补丁"):
            mod.verify_baseline(memory, base)
        self.assertEqual(memory.writes, [])


if __name__ == "__main__":
    unittest.main()
