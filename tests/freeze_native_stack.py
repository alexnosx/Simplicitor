"""Read native stacks of an owned pytest child with Windows' existing DbgHelp.

No debugger or symbols are installed. Each thread is suspended only while its
context and stack are read, then resumed in finally. Export names are approximate
without private PDBs; offsets are retained rather than treated as exact symbols.
"""
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import sys


class Address(C.Structure):
    _fields_ = [("offset", C.c_ulonglong), ("segment", W.WORD), ("mode", C.c_int)]


class Frame(C.Structure):
    _fields_ = [("pc", Address), ("ret", Address), ("frame", Address),
                ("stack", Address), ("store", Address), ("table", C.c_void_p),
                ("params", C.c_ulonglong * 4), ("far", W.BOOL), ("virtual", W.BOOL),
                ("reserved", C.c_ulonglong * 3), ("help", C.c_ulonglong * 14)]


class Symbol(C.Structure):
    _fields_ = [("size", W.ULONG), ("type", W.ULONG), ("reserved", C.c_ulonglong * 2),
                ("index", W.ULONG), ("length", W.ULONG), ("base", C.c_ulonglong),
                ("flags", W.ULONG), ("value", C.c_ulonglong), ("address", C.c_ulonglong),
                ("register", W.ULONG), ("scope", W.ULONG), ("tag", W.ULONG),
                ("name_length", W.ULONG), ("max_name", W.ULONG), ("name", C.c_char * 1)]


class ThreadEntry(C.Structure):
    _fields_ = [("size", W.DWORD), ("usage", W.DWORD), ("tid", W.DWORD),
                ("pid", W.DWORD), ("base", W.LONG), ("delta", W.LONG), ("flags", W.DWORD)]


def capture(pid, output):
    """Capture only the requested owned process, recording unavailable symbols honestly."""
    kernel = C.WinDLL("kernel32", use_last_error=True)
    dbg = C.WinDLL("dbghelp", use_last_error=True)
    signatures = {
        "OpenProcess": ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
        "OpenThread": ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
        "CloseHandle": ([W.HANDLE], W.BOOL),
        "SuspendThread": ([W.HANDLE], W.DWORD),
        "ResumeThread": ([W.HANDLE], W.DWORD),
        "GetThreadContext": ([W.HANDLE, C.c_void_p], W.BOOL),
        "CreateToolhelp32Snapshot": ([W.DWORD, W.DWORD], W.HANDLE),
        "Thread32First": ([W.HANDLE, C.POINTER(ThreadEntry)], W.BOOL),
        "Thread32Next": ([W.HANDLE, C.POINTER(ThreadEntry)], W.BOOL),
    }
    for name, (args, result) in signatures.items():
        fn = getattr(kernel, name)
        fn.argtypes, fn.restype = args, result
    dbg.SymSetOptions.argtypes, dbg.SymSetOptions.restype = [W.DWORD], W.DWORD
    dbg.SymInitialize.argtypes = [W.HANDLE, C.c_char_p, W.BOOL]
    dbg.SymInitialize.restype = W.BOOL
    dbg.SymCleanup.argtypes, dbg.SymCleanup.restype = [W.HANDLE], W.BOOL
    dbg.StackWalk64.argtypes = [W.DWORD, W.HANDLE, W.HANDLE, C.POINTER(Frame),
                               C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p]
    dbg.StackWalk64.restype = W.BOOL
    dbg.SymFromAddr.argtypes = [W.HANDLE, C.c_ulonglong, C.POINTER(C.c_ulonglong),
                               C.POINTER(Symbol)]
    dbg.SymFromAddr.restype = W.BOOL
    dbg.SymGetModuleBase64.argtypes = [W.HANDLE, C.c_ulonglong]
    dbg.SymGetModuleBase64.restype = C.c_ulonglong
    psapi = C.WinDLL("psapi", use_last_error=True)
    psapi.GetModuleBaseNameW.argtypes = [W.HANDLE, W.HMODULE, W.LPWSTR, W.DWORD]
    psapi.GetModuleBaseNameW.restype = W.DWORD
    process = kernel.OpenProcess(0x410, False, pid)  # QUERY_INFORMATION | VM_READ
    if not process:
        raise C.WinError(C.get_last_error())
    rows = []
    initialized = False
    try:
        # Only local/export symbols: explicitly ignore inherited symbol-server paths.
        dbg.SymSetOptions(0x2 | 0x4 | 0x1000 | 0x80000)  # UNDNAME, DEFERRED, IGNORE, NO_PROMPTS
        initialized = bool(dbg.SymInitialize(process, b".", True))
        if not initialized:
            raise C.WinError(C.get_last_error())
        snapshot = kernel.CreateToolhelp32Snapshot(4, 0)
        if snapshot == C.c_void_p(-1).value:
            raise C.WinError(C.get_last_error())
        tids = []
        try:
            entry = ThreadEntry()
            entry.size = C.sizeof(entry)
            ok = kernel.Thread32First(snapshot, C.byref(entry))
            while ok:
                if entry.pid == pid:
                    tids.append(entry.tid)
                ok = kernel.Thread32Next(snapshot, C.byref(entry))
        finally:
            kernel.CloseHandle(snapshot)
        for tid in tids:
            row = {"tid": tid, "hex_tid": hex(tid), "frames": []}
            rows.append(row)
            thread = kernel.OpenThread(0x2 | 0x8 | 0x40, False, tid)
            if not thread:
                row["error"] = C.get_last_error()
                continue
            suspended = False
            try:
                if kernel.SuspendThread(thread) == 0xFFFFFFFF:
                    row["error"] = C.get_last_error()
                    continue
                suspended = True
                raw = C.create_string_buffer(1232 + 16)
                address = (C.addressof(raw) + 15) & ~15
                C.c_uint32.from_address(address + 48).value = 0x10000B  # AMD64 CONTEXT_FULL
                if not kernel.GetThreadContext(thread, address):
                    row["error"] = C.get_last_error()
                    continue
                frame = Frame()
                for field, offset in (("pc", 248), ("stack", 152), ("frame", 160)):
                    getattr(frame, field).offset = C.c_ulonglong.from_address(address + offset).value
                    getattr(frame, field).mode = 3  # AddrModeFlat
                for index in range(64):
                    pc = frame.pc.offset
                    if not pc:
                        break
                    base = dbg.SymGetModuleBase64(process, pc)
                    module = C.create_unicode_buffer(260)
                    psapi.GetModuleBaseNameW(process, base, module, len(module))
                    symbol_raw = C.create_string_buffer(C.sizeof(Symbol) + 2048)
                    symbol = C.cast(symbol_raw, C.POINTER(Symbol))
                    symbol.contents.size, symbol.contents.max_name = C.sizeof(Symbol), 2048
                    displacement = C.c_ulonglong()
                    known = dbg.SymFromAddr(process, pc, C.byref(displacement), symbol)
                    name = C.string_at(C.addressof(symbol.contents) + Symbol.name.offset,
                                       symbol.contents.name_length).decode("utf-8", "replace") if known else None
                    row["frames"].append({"pc": hex(pc), "module": module.value,
                                           "module_offset": hex(pc - base) if base else None,
                                           "nearest_symbol": name,
                                           "symbol_offset": hex(displacement.value) if known else None})
                    previous = frame.pc.offset, frame.stack.offset
                    if not dbg.StackWalk64(0x8664, process, thread, C.byref(frame), address, None,
                                           C.cast(dbg.SymFunctionTableAccess64, C.c_void_p),
                                           C.cast(dbg.SymGetModuleBase64, C.c_void_p), None):
                        break
                    if index and previous == (frame.pc.offset, frame.stack.offset):
                        break
            finally:
                if suspended:
                    kernel.ResumeThread(thread)
                kernel.CloseHandle(thread)
        Path(output).write_text(json.dumps({"pid": pid, "threads": rows}, indent=2) + "\n",
                                encoding="utf-8")
    finally:
        if initialized:
            dbg.SymCleanup(process)
        kernel.CloseHandle(process)


if __name__ == "__main__":
    capture(int(sys.argv[1]), sys.argv[2])
