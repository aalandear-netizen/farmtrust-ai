"""Pytest configuration and fixtures for backend tests."""
import asyncio
import sys
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# ── SQLite compatibility: map JSONB → JSON ────────────────────────────────────
def _patch_sqlite_types():
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
    if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
        SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON


_patch_sqlite_types()


# ── SQLite compatibility: disable geoalchemy2 column_expression wrapping ─────
def _patch_geometry_column_expression():
    """
    Geoalchemy2's Geometry.column_expression wraps SELECT columns with AsEWKB().
    On plain SQLite (no SpatiaLite) that function doesn't exist.
    Return the column as-is so tests can pass without SpatiaLite installed.
    """
    try:
        from geoalchemy2.types import _GISType
        _orig_col_expr = _GISType.column_expression

        def _col_expr_passthrough(self, col):
            if self.as_binary is None:
                return None
            # Detect SQLite by checking if the column is already in SQLite context.
            # We can't easily detect dialect at this point, so we disable for all
            # dialects in tests by checking the function name availability.
            try:
                return _orig_col_expr(self, col)
            except Exception:
                return None

        # In test mode: return column as-is for SELECT (no AsEWKB wrapping)
        # and skip bind_expression for INSERT (no GeomFromEWKT wrapping).
        _GISType.column_expression = lambda self, col: col
        _GISType.bind_expression = lambda self, bindvalue: bindvalue
    except ImportError:
        pass


_patch_geometry_column_expression()


# ── SQLite compatibility: patch geoalchemy2 admin to skip SpatiaLite calls ───
def _patch_geoalchemy2_for_sqlite():
    """
    Geoalchemy2's SQLite dialect calls SpatiaLite functions (RecoverGeometryColumn,
    DiscardGeometryColumn, etc.) in its after_create / before_drop hooks.
    We replace those with no-ops so plain SQLite works for unit tests.
    The before_create hook is still needed because it converts the Geometry column
    type to _DummyGeometry so that the CREATE TABLE DDL emits valid SQLite syntax.
    """
    try:
        import geoalchemy2.admin as ga_admin
        from geoalchemy2.admin import dialects as ga_dialects

        class _SQLiteTestDialect:
            before_create = staticmethod(ga_dialects.sqlite.before_create)
            after_drop = staticmethod(ga_dialects.sqlite.after_drop)

            @staticmethod
            def after_create(table, bind, **kw):
                # Restore the _saved_columns so the table object is consistent,
                # but skip any SpatiaLite SQL calls.
                _SQLiteTestDialect.after_drop(table, bind, **kw)

            @staticmethod
            def before_drop(*a, **kw):
                pass  # Skip DiscardGeometryColumn

        _sqlite_test = _SQLiteTestDialect()
        _orig_select = ga_admin.select_dialect

        def _patched_select(dialect_name):
            if dialect_name == "sqlite":
                return _sqlite_test
            return _orig_select(dialect_name)

        # Patch the module-level name so the registered event closures pick it up
        sys.modules["geoalchemy2.admin"].select_dialect = _patched_select
    except ImportError:
        pass


_patch_geoalchemy2_for_sqlite()

# ─────────────────────────────────────────────────────────────────────────────

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(_create_tables_safe)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(_drop_tables_safe)


def _create_tables_safe(sync_conn):
    """Create all tables, silently skipping any that fail on SQLite."""
    for table in Base.metadata.sorted_tables:
        try:
            table.create(sync_conn, checkfirst=True)
        except Exception:
            pass


def _drop_tables_safe(sync_conn):
    """Drop all tables, silently skipping any that fail."""
    for table in reversed(Base.metadata.sorted_tables):
        try:
            table.drop(sync_conn, checkfirst=True)
        except Exception:
            pass


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP test client with the test database."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

