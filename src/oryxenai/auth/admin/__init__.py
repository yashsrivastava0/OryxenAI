"""Server-only administrator lifecycle boundary."""

from oryxenai.auth.admin.provider import SupabaseAdminProvider
from oryxenai.auth.admin.service import AdminService

__all__ = ["AdminService", "SupabaseAdminProvider"]
