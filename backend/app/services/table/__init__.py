"""Table structure recognition and fallback module."""

from app.services.table.base import TableStructureProvider
from app.services.table.paddle_table_provider import PaddleTableStructureProvider
from app.services.table.table_service import TableService

__all__ = [
    "TableStructureProvider",
    "PaddleTableStructureProvider",
    "TableService",
]
