"""Read-only camera-state probe for the inspected NBA 2K27 build."""
import argparse, ctypes as C, json, struct
from ctypes import wintypes as W
from pathlib import Path

K=C.WinDLL('kernel32',use_last_error=True)
SIZE=C.c_size_t
class PROCESSENTRY32W(C.Structure):
 _fields_=[('dwSize',W.DWORD),('cntUsage',W.DWORD),('th32ProcessID',W.DWORD),('th32DefaultHeapID',SIZE),('th32ModuleID',W.DWORD),('cntThreads',W.DWORD),('th32ParentProcessID',W.DWORD),('pcPriClassBase',W.LONG),('dwFlags',W.DWORD),('szExeFile',W.WCHAR*260)]
class MODULEENTRY32W(C.Structure):
 _fields_=[('dwSize',W.DWORD),('th32ModuleID',W.DWORD),('th32ProcessID',W.DWORD),('GlblcntUsage',W.DWORD),('ProccntUsage',W.DWORD),('modBaseAddr',C.c_void_p),('modBaseSize',W.DWORD),('hModule',W.HMODULE),('szModule',W.WCHAR*256),('szExePath',W.WCHAR*260)]
K.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD];K.CreateToolhelp32Snapshot.restype=W.HANDLE
K.CloseHandle.argtypes=[W.HANDLE];K.CloseHandle.restype=W.BOOL
for name,typ in [('Process32FirstW',PROCESSENTRY32W),('Process32NextW',PROCESSENTRY32W),('Module32FirstW',MODULEENTRY32W),('Module32NextW',MODULEENTRY32W)]:
 fn=getattr(K,name);fn.argtypes=[W.HANDLE,C.POINTER(typ)];fn.restype=W.BOOL
K.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];K.OpenProcess.restype=W.HANDLE
K.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,SIZE,C.POINTER(SIZE)];K.ReadProcessMemory.restype=W.BOOL

def snapshot(flags,pid,typ,first,next_):
 h=K.CreateToolhelp32Snapshot(flags,pid)
 if h==C.c_void_p(-1).value: raise C.WinError(C.get_last_error())
 try:
  entry=typ();entry.dwSize=C.sizeof(entry)
  ok=getattr(K,first)(h,C.byref(entry))
  while ok:
   yield typ.from_buffer_copy(entry)
   ok=getattr(K,next_)(h,C.byref(entry))
 finally: K.CloseHandle(h)

def capture():
 matches=[p for p in snapshot(2,0,PROCESSENTRY32W,'Process32FirstW','Process32NextW') if p.szExeFile.lower()=='nba2k27.exe']
 if len(matches)!=1: raise RuntimeError(f'Expected one NBA2K27.exe process; found {len(matches)}. Start the game and pause in a match.')
 pid=matches[0].th32ProcessID
 modules=list(snapshot(0x18,pid,MODULEENTRY32W,'Module32FirstW','Module32NextW'))
 module=next(m for m in modules if m.szModule.lower()=='nba2k27.exe')
 base=module.modBaseAddr
 h=K.OpenProcess(0x1010,False,pid)
 if not h: raise C.WinError(C.get_last_error())
 try:
  def read(rva,n):
   buf=C.create_string_buffer(n);done=SIZE()
   if not K.ReadProcessMemory(h,base+rva,buf,n,C.byref(done)) or done.value!=n: raise C.WinError(C.get_last_error())
   return buf.raw
  # Reject other versions or altered entry bytes before interpreting addresses.
  expected=bytes.fromhex('41 56 56 57 55 53 48 83 ec 60 89 cf')
  actual=read(0xc2d000,len(expected))
  if actual!=expected: raise RuntimeError('Camera function signature differs; offsets must be inspected again. No writes performed.')
  ids=struct.unpack('<ii',read(0xa67be00,8))
  return {'pid':pid,'module_base':hex(base),'module_path':module.szExePath,'candidate_active_camera_ids':list(ids),'candidate_validity_flags':list(read(0xa67c430,72)),'note':'Read-only candidate fields; identify their meaning by comparing camera selections. No memory or file patch applied.'}
 finally: K.CloseHandle(h)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
 try:
  result=capture();payload=json.dumps(result,indent=2);print(payload)
  if args.output:args.output.write_text(payload,encoding='utf-8')
 except (OSError,RuntimeError,StopIteration) as e:
  print(f'Probe unavailable: {e}');raise SystemExit(1)
