from io import BytesIO
from pathlib import Path

from stealer_parser.containers import AppContainer
from stealer_parser.models import ArchiveWrapper
from stealer_parser.services.leak_processor import LeakProcessor
from zipfile import ZipFile


def test_process_data_test_zip():
    # Skip if test.zip not present
    zip_path = Path("data/test.zip")
    if not zip_path.exists():
        return

    app = AppContainer()
    app.init_resources()
    try:
        leak_processor: LeakProcessor = app.leak_processor()
        with open(zip_path, "rb") as fh:
            buf = BytesIO(fh.read())
        archive = ArchiveWrapper(ZipFile(buf), filename=str(zip_path))
        try:
            leak = leak_processor.process_leak(archive)
        finally:
            archive.close()
        assert leak.systems, "Should parse at least one system from data/test.zip"
    finally:
        app.shutdown_resources()
