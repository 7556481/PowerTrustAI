// Diagnostic-only. Observe this one process and explicit derived-index roots.
// Ordinary mode never changes arguments, return values, or error codes.
const cfg = CONFIG;
const normalize = p => p.replace(/^\\\\\?\\/, '').replace(/^\\\?\?\\/, '').replaceAll('/', '\\').toLowerCase();
const roots = cfg.roots.map(normalize);
const scoped = p => roots.some(r => normalize(p).startsWith(r + '\\'));
const handles = new Map();
const fileWrites = new Map();
let phase = 'attached-before-admission', injected = false;
let operations = 0, writeBytes = 0, sequence = 0;
const k = Process.getModuleByName('kernel32.dll');
const mkdir = new NativeFunction(k.getExportByName('CreateDirectoryW'), 'bool', ['pointer', 'pointer']);
const ntToWin = new NativeFunction(Process.getModuleByName('ntdll.dll').getExportByName('RtlNtStatusToDosError'), 'uint32', ['uint32']);
function event(operation, path, fields = {}) {
  send({operation, path, pid: Process.id, thread: Process.getCurrentThreadId(), wall_ms: Date.now(), sequence: sequence++, phase, ...fields});
}
function inject(path) {
  if (cfg.inject_pos_failure && !injected && scoped(path) && path.endsWith('.pos')) {
    injected = true;
    const actual = path.replace(/^\\\?\?\\/, '');
    const made = mkdir(Memory.allocUtf16String(actual), ptr(0));
    event('synthetic_file_collision', path, {created_directory: made, synthetic: true});
  }
}
function install(module, name, callbacks) {
  const address = Process.getModuleByName(module).findExportByName(name);
  if (address === null) throw new Error('Required trace boundary missing: ' + name);
  Interceptor.attach(address, callbacks);
}
install('kernel32.dll', 'OutputDebugStringW', {
  onEnter(a) {
    const s = a[0].readUtf16String();
    if (s.startsWith('PTAI_NATIVE_PHASE:')) { phase = s.slice(18); event('phase', '', {}); }
  }
});
install('ntdll.dll', 'NtCreateFile', {
  onEnter(a) {
    this.path = null; this.output = a[0];
    try {
      const us = a[2].add(16).readPointer();
      const path = us.add(8).readPointer().readUtf16String(us.readU16() / 2);
      if (scoped(path)) { this.path = path; this.access = a[1].toUInt32(); this.disposition = a[7].toUInt32(); this.options = a[8].toUInt32(); inject(path); }
    } catch (_) { /* Other unscoped OS operations are not diagnostic inputs. */ }
  },
  onLeave(ret) {
    if (!this.path) return;
    const saved = this.lastError, status = ret.toInt32();
    if (status >= 0) handles.set(this.output.readPointer().toString(), this.path);
    event('NtCreateFile', this.path, {ntstatus: '0x' + (status >>> 0).toString(16), failed: status < 0, winerror: status < 0 ? ntToWin(status >>> 0) : null, access: this.access, disposition: this.disposition, options: this.options});
    this.lastError = saved;
  }
});
install('kernel32.dll', 'CreateFileW', {
  onEnter(a) { this.path = a[0].readUtf16String(); this.keep = scoped(this.path); },
  onLeave(ret) {
    const saved = this.lastError;
    if (this.keep) {
      const failed = ret.equals(ptr(-1));
      if (!failed) handles.set(ret.toString(), this.path);
      event('CreateFileW', this.path, {failed, winerror: failed ? saved : null});
    }
    this.lastError = saved;
  }
});
// The actual Rust Windows implementation can bypass Win32 WriteFile/CloseHandle
// and call NT directly. Positive selfcheck must observe these real writes.
for (const name of ['NtWriteFile', 'NtReadFile', 'NtFlushBuffersFile', 'NtSetInformationFile', 'NtClose']) {
  install('ntdll.dll', name, {
    onEnter(a) {
      this.handle = a[0].toString(); this.path = handles.get(this.handle);
      if (name === 'NtWriteFile') this.bytes = a[6].toUInt32();
      if (name === 'NtSetInformationFile') this.infoClass = a[4].toUInt32();
    },
    onLeave(ret) {
      if (!this.path) return;
      const saved = this.lastError, status = ret.toInt32(), failed = status < 0;
      operations++;
      if (name === 'NtWriteFile' && status === 0) {
        writeBytes += this.bytes;
        const stats = fileWrites.get(this.handle) || {calls: 0, bytes: 0};
        stats.calls++; stats.bytes += this.bytes; fileWrites.set(this.handle, stats);
      }
      if (failed || name === 'NtSetInformationFile') event(name, this.path, {failed,
        ntstatus: '0x' + (status >>> 0).toString(16), winerror: failed ? ntToWin(status >>> 0) : null, infoClass: this.infoClass});
      if (name === 'NtClose' && status === 0) {
        const stats = fileWrites.get(this.handle);
        if (stats) { event('close_write_summary', this.path, stats); fileWrites.delete(this.handle); }
        handles.delete(this.handle);
      }
      this.lastError = saved;
    }
  });
}
for (const name of ['WriteFile', 'FlushFileBuffers', 'SetFileInformationByHandle', 'CloseHandle']) {
  install('kernel32.dll', name, {
    onEnter(a) { this.handle = a[0].toString(); this.path = handles.get(this.handle); if (name === 'WriteFile') this.bytes = a[2].toUInt32(); },
    onLeave(ret) {
      const saved = this.lastError;
      if (this.path) {
        const failed = ret.toInt32() === 0;
        operations++;
        // Counts come from NT only, avoiding double counting Win32 wrappers.
        if (failed || name === 'SetFileInformationByHandle') event(name, this.path, {failed, winerror: failed ? saved : null});
        if (name === 'CloseHandle' && !failed) {
          const stats = fileWrites.get(this.handle);
          if (stats) { event('close_write_summary', this.path, stats); fileWrites.delete(this.handle); }
          handles.delete(this.handle);
        }
      }
      this.lastError = saved;
    }
  });
}
for (const name of ['MoveFileExW', 'ReplaceFileW', 'DeleteFileW']) {
  install('kernel32.dll', name, {
    onEnter(a) {
      this.path = a[0].readUtf16String(); this.keep = scoped(this.path);
      this.to = name === 'DeleteFileW' || a[1].isNull() ? null : a[1].readUtf16String();
      if (this.to && scoped(this.to)) this.keep = true;
    },
    onLeave(ret) {
      const saved = this.lastError;
      if (this.keep) event(name, this.path, {to: this.to, failed: ret.toInt32() === 0, winerror: ret.toInt32() === 0 ? saved : null});
      this.lastError = saved;
    }
  });
}
// Rust's existing panic hook/backtrace stays on captured stderr. Do not install
// an exception handler: OutputDebugString itself raises normal debug exceptions.
rpc.exports = { summary() { return {operations, writeBytes, trackedHandles: handles.size, phase, injected}; } };
event('trace_ready', '', {version: 8, roots: cfg.roots, synthetic: cfg.inject_pos_failure});
