from pathlib import Path

from stealer_parser.containers import AppContainer
from stealer_parser.models.directory_wrapper import DirectoryArchiveWrapper
from stealer_parser.services.leak_processor import LeakProcessor


def test_process_data_test_dir():
    dir_path = Path("data/test")
    if not dir_path.exists():
        return

    app = AppContainer()
    app.init_resources()
    try:
        leak_processor: LeakProcessor = app.leak_processor()
        archive = DirectoryArchiveWrapper(dir_path)
        try:
            leak = leak_processor.process_leak(archive)
        finally:
            archive.close()
        assert leak.systems, "Should parse at least one system from data/test/"
    finally:
        app.shutdown_resources()
