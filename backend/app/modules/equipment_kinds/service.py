"""Kind code invariants. Only labels/status are mutable, not the stable code."""
from fastapi import HTTPException


def require_active_kind(kind):
    if kind is None or not kind.active:
        raise HTTPException(422, 'Jenis peralatan tidak aktif atau tidak ditemukan')
