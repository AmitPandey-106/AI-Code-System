"""Own test-process descendants until completion (Windows Job / POSIX group)."""
import os
import signal


class ProcessTree:
    def __init__(self, process):
        self.process = process
        self.job = None
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes as w
            class Basic(ctypes.Structure):
                _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                            ("flags", w.DWORD), ("min_ws", ctypes.c_size_t),
                            ("max_ws", ctypes.c_size_t), ("active", w.DWORD),
                            ("affinity", ctypes.c_size_t), ("priority", w.DWORD),
                            ("scheduling", w.DWORD)]
            class IO(ctypes.Structure):
                _fields_ = [(n, ctypes.c_uint64) for n in ("ro", "wo", "oo", "rt", "wt", "ot")]
            class Extended(ctypes.Structure):
                _fields_ = [("basic", Basic), ("io", IO), ("process_mem", ctypes.c_size_t),
                            ("job_mem", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                            ("peak_job", ctypes.c_size_t)]
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
            kernel.CreateJobObjectW.restype = w.HANDLE
            kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
            kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
            kernel.CloseHandle.argtypes = [w.HANDLE]
            self.kernel = kernel
            job = kernel.CreateJobObjectW(None, None)
            info = Extended()
            info.basic.flags = 0x2000
            if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
                if job:
                    kernel.CloseHandle(job)
                raise OSError(ctypes.get_last_error(), "Cannot configure test process job")
            if not kernel.AssignProcessToJobObject(job, w.HANDLE(int(process._handle))):
                kernel.CloseHandle(job)
                raise OSError(ctypes.get_last_error(), "Cannot own test process tree")
            self.job = job

    def stop(self):
        if os.name == "nt":
            if self.job:
                self.kernel.CloseHandle(self.job)
                self.job = None
            elif self.process.poll() is None:
                self.process.kill()
        else:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.process.wait(timeout=5)
