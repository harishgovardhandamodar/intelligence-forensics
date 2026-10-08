"""GPU / NCCL crash dumps (staged, exotic). 1/100 whole, 96-char head."""
from __future__ import annotations
from .staged import StagedSurface
class GpuDebugSurface(StagedSurface):
    id = "gpu_debug"; title = "GPU debug dumps"
    rate_num = 1; rate_den = 100; head_chars = 96
SURFACE = GpuDebugSurface()
