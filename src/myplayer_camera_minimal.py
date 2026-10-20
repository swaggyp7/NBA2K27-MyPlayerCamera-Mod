"""NBA 2K27 自创球员摄影机：仅修改菜单数据的离线测试版。"""
import argparse
import ctypes as C
import struct
from ctypes import wintypes as W

import camera_state as state

K = state.K
LIST_RVA = 0x9963330
DESC_RVAS = [0x992c6b0, 0x992c6c0, 0x992c6d0] + list(range(0x992c7b0, 0x992c820, 16))
FLAG_RVA = 0xa67c453  # Camera ID 35 in the 72-byte availability array.
ACTIVE_RVA = 0xa67be00
CODE_SIGNATURES = {
    0xc2d000: bytes.fromhex("41 56 56 57 55 53 48 83 ec 60 89 cf"),
    0xc2cd7d: bytes.fromhex("48 63 07 48 89 c1"),
}
BASELINE = [1, 2, 3, 4, 15, 8, 9, 16, 17, 19, 20, 22, 23, 0]

K.WriteProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
K.WriteProcessMemory.restype = W.BOOL
K.VirtualAllocEx.argtypes = [W.HANDLE, C.c_void_p, C.c_size_t, W.DWORD, W.DWORD]
K.VirtualAllocEx.restype = C.c_void_p
K.VirtualFreeEx.argtypes = [W.HANDLE, C.c_void_p, C.c_size_t, W.DWORD]
K.VirtualFreeEx.restype = W.BOOL
K.VirtualProtectEx.argtypes = [W.HANDLE, C.c_void_p, C.c_size_t, W.DWORD, C.POINTER(W.DWORD)]
K.VirtualProtectEx.restype = W.BOOL
K.GetExitCodeProcess.argtypes = [W.HANDLE, C.POINTER(W.DWORD)]
K.GetExitCodeProcess.restype = W.BOOL


def find_game():
    processes = list(state.snapshot(2, 0, state.PROCESSENTRY32W, "Process32FirstW", "Process32NextW"))
    if any("easyanticheat" in p.szExeFile.lower() or p.szExeFile.lower() == "start_protected_game.exe" for p in processes):
        raise RuntimeError("检测到 EAC 或受保护启动器；请只在离线且未启用 EAC 的游戏中使用。")
    games = [p for p in processes if p.szExeFile.lower() == "nba2k27.exe"]
    if len(games) != 1:
        raise RuntimeError(f"需要一个正在运行的 NBA2K27.exe；当前找到 {len(games)} 个。")
    pid = games[0].th32ProcessID
    modules = state.snapshot(0x18, pid, state.MODULEENTRY32W, "Module32FirstW", "Module32NextW")
    module = next((m for m in modules if m.szModule.lower() == "nba2k27.exe"), None)
    if module is None:
        raise RuntimeError("未找到游戏主模块。")
    return pid, module.modBaseAddr


class GameMemory:
    def __init__(self, pid):
        self.handle = K.OpenProcess(0x1038, False, pid)  # query, VM operation, read, write
        if not self.handle:
            raise C.WinError(C.get_last_error())

    def close(self):
        K.CloseHandle(self.handle)

    def alive(self):
        code = W.DWORD()
        if not K.GetExitCodeProcess(self.handle, C.byref(code)):
            raise C.WinError(C.get_last_error())
        return code.value == 259

    def read(self, address, size):
        buffer = C.create_string_buffer(size)
        done = C.c_size_t()
        if not K.ReadProcessMemory(self.handle, address, buffer, size, C.byref(done)) or done.value != size:
            raise C.WinError(C.get_last_error())
        return buffer.raw

    def write(self, address, data):
        # Only data descriptors and one availability byte are written; code pages are never touched.
        old = W.DWORD()
        if not K.VirtualProtectEx(self.handle, address, len(data), 0x04, C.byref(old)):
            raise C.WinError(C.get_last_error())
        try:
            done = C.c_size_t()
            buffer = C.create_string_buffer(data)
            if not K.WriteProcessMemory(self.handle, address, buffer, len(data), C.byref(done)) or done.value != len(data):
                raise C.WinError(C.get_last_error())
            if self.read(address, len(data)) != data:
                raise RuntimeError("写入校验失败。")
        finally:
            ignored = W.DWORD()
            if not K.VirtualProtectEx(self.handle, address, len(data), old.value, C.byref(ignored)):
                raise C.WinError(C.get_last_error())

    def allocate_list(self, data):
        address = K.VirtualAllocEx(self.handle, None, 4096, 0x3000, 0x04)
        if not address:
            raise C.WinError(C.get_last_error())
        try:
            self.write(address, data)
            return address
        except BaseException:
            K.VirtualFreeEx(self.handle, address, 0, 0x8000)
            raise


def verify_baseline(memory, base):
    for rva, expected in CODE_SIGNATURES.items():
        if memory.read(base + rva, len(expected)) != expected:
            raise RuntimeError("发现旧版代码补丁或不同的游戏代码；请完全重启游戏，不要叠加使用。")
    original_list = base + LIST_RVA
    if memory.read(original_list, 56) != struct.pack("<14I", *BASELINE):
        raise RuntimeError("原始镜头列表不匹配；未作修改。")
    expected = struct.pack("<QI", original_list, 14)
    if any(memory.read(base + rva, 12) != expected for rva in DESC_RVAS):
        raise RuntimeError("列表已有修改或与预期不符；请完全重启游戏。")
    flag = memory.read(base + FLAG_RVA, 1)
    if flag not in (b"\x00", b"\x01"):
        raise RuntimeError("镜头可选标记不符合预期；未作修改。")
    return flag


def set_descriptor(memory, address, pointer, count):
    # New array has an extra slot. On restore, shorten count before switching back.
    memory.write(address, struct.pack("<Q", pointer))
    memory.write(address + 8, struct.pack("<I", count))


def restore_descriptor(memory, address, pointer):
    memory.write(address + 8, struct.pack("<I", 14))
    memory.write(address, struct.pack("<Q", pointer))


def run(check=False):
    pid, base = find_game()
    memory = GameMemory(pid)
    allocation = None
    changed = []
    flag_changed = False
    original_flag = None
    original_list = base + LIST_RVA
    try:
        original_flag = verify_baseline(memory, base)
        print(f"游戏 PID {pid}，代码与原始列表校验通过；镜头 35 可选标记={original_flag[0]}。", flush=True)
        if check:
            return
        allocation = memory.allocate_list(struct.pack("<15I", *(BASELINE + [35])))
        try:
            for rva in DESC_RVAS:
                address = base + rva
                changed.append(address)  # Include partially written descriptor in rollback.
                set_descriptor(memory, address, allocation, 15)
            if original_flag == b"\x00":
                flag_changed = True
                memory.write(base + FLAG_RVA, b"\x01")
            if any(memory.read(base + rva, 12) != struct.pack("<QI", allocation, 15) for rva in DESC_RVAS):
                raise RuntimeError("启用后列表校验失败。")
            if memory.read(base + FLAG_RVA, 1) != b"\x01":
                raise RuntimeError("启用后可选标记校验失败。")
            for rva, expected in CODE_SIGNATURES.items():
                if memory.read(base + rva, len(expected)) != expected:
                    raise RuntimeError("代码在启用过程中被其他程序改动。")
            print("已启用：10 处菜单列表引用新增自创球员镜头；游戏代码保持原样。", flush=True)
            print("请先测试选项、死球恢复和下一场开球。测试期间保持此窗口打开。", flush=True)
            while memory.alive():
                input("恢复原始列表前，先切回普通 2K 镜头，再按回车：")
                if not memory.alive():
                    break
                active = struct.unpack("<ii", memory.read(base + ACTIVE_RVA, 8))
                if 35 in active:
                    print("当前仍选中自创球员镜头，请先切回普通镜头。", flush=True)
                    continue
                break
        finally:
            if memory.alive():
                if changed and 35 in struct.unpack("<ii", memory.read(base + ACTIVE_RVA, 8)):
                    raise RuntimeError("仍在使用自创球员镜头；保留本次内存列表。请退出游戏清除补丁。")
                # On an unexpected write failure, restoration still covers the in-progress descriptor.
                # Leave the allocation allocated if a descriptor was externally changed.
                for address in reversed(changed):
                    current = memory.read(address, 12)
                    if current[:8] not in (struct.pack("<Q", allocation), struct.pack("<Q", original_list)):
                        raise RuntimeError("列表被其他程序改动；请退出游戏清除本次内存修改。")
                    restore_descriptor(memory, address, original_list)
                if flag_changed and memory.read(base + FLAG_RVA, 1) == b"\x01":
                    memory.write(base + FLAG_RVA, original_flag)
                # An already-open menu may retain the new list pointer briefly.
                # Keep its 4 KB allocation until the game process exits.
                if allocation and not changed:
                    K.VirtualFreeEx(memory.handle, allocation, 0, 0x8000)
                print("已恢复原始列表和可选标记。", flush=True)
    finally:
        memory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只读校验兼容性与旧补丁状态")
    args = parser.parse_args()
    try:
        run(args.check)
    except (OSError, RuntimeError, StopIteration, KeyboardInterrupt, EOFError) as exc:
        print(f"操作结束：{exc}")
        raise SystemExit(1)
