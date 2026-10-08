"""Backup snapshots (staged). 1/50 whole nightly snapshots, no heads."""
from __future__ import annotations
from .staged import StagedSurface
class BackupSnapshotSurface(StagedSurface):
    id = "backup_snapshot"; title = "Backup snapshots"
    rate_num = 1; rate_den = 50; head_chars = 0
SURFACE = BackupSnapshotSurface()
