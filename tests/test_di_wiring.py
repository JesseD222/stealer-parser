import types
import contextlib

import pytest

from stealer_parser.containers import AppContainer


@pytest.fixture
def container():
    c = AppContainer()
    c.wire(modules=[__name__])
    c.init_resources()
    try:
        yield c
    finally:
        c.shutdown_resources()
        c.unwire()


def test_can_resolve_core_services(container: AppContainer):
    logger = container.logger()
    assert logger is not None

    # Parser registry is a Singleton and should be instantiable
    registry = container.parser_registry()
    assert registry is not None

    # Leak processor should resolve and accept the registry
    leak_processor = container.leak_processor()
    assert leak_processor is not None


def test_exporter_constructible_with_db_pool_override(container: AppContainer, monkeypatch):
    # Provide a fake pool with getconn/putconn so exporter can initialize
    class FakeConn:
        def cursor(self):
            class Ctx:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def execute(self, *args, **kwargs):
                    return None
            return Ctx()

        def commit(self):
            pass

    class FakePool:
        def getconn(self):
            return FakeConn()
        def putconn(self, _):
            pass
        def closeall(self):
            pass

    # Override db_pool resource with a ready FakePool instance
    container.database.db_pool.override(FakePool())

    exporter = container.services.postgres_exporter()
    assert exporter is not None

    # Test connection should succeed with fake pool
    assert exporter.test_connection() is True
