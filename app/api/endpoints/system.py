from fastapi import APIRouter
import platform, os, time, psutil, socket
from datetime import datetime, timezone

system_router = APIRouter()

try:
    import psutil  # type: ignore
    HAVE_PSUTIL = True
except Exception:  # pragma: no cover
    HAVE_PSUTIL = False

START_TIME = time.time()

@system_router.get("/diagnostics", summary="Extended diagnostics")
async def diagnostics():
    """Return extended runtime diagnostics for debugging 502 or performance issues."""
    load_avg = None
    if hasattr(os, 'getloadavg'):
        try:
            load_avg = os.getloadavg()
        except Exception:
            load_avg = None
    mem = None
    cpu = None
    if HAVE_PSUTIL:
        try:
            mem = psutil.virtual_memory()._asdict()
            cpu = {
                "count": psutil.cpu_count(),
                "percent": psutil.cpu_percent(interval=0.1),
            }
        except Exception:
            pass
    return {
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "uptime_sec": int(time.time() - START_TIME),
        "load_avg": load_avg,
        "memory": mem,
        "cpu": cpu,
        "env_debug": os.getenv("DEBUG"),
        "cwd": os.getcwd(),
    }
