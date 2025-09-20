"""Infostealer logs parser."""
from argparse import Namespace
from typing import Optional
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from dependency_injector.wiring import inject, Provide
from py7zr import SevenZipFile
from rarfile import RarFile
from verboselogs import VerboseLogger
from stealer_parser.containers import AppContainer
from stealer_parser.database.postgres import PostgreSQLExporter
from stealer_parser.helpers import parse_options
from stealer_parser.models import ArchiveWrapper, Leak
from stealer_parser.services.leak_processor import LeakProcessor
from stealer_parser.config import Settings

def read_archive(
    buffer: BytesIO, filename: str, password: str | None
) -> ArchiveWrapper:
    """Open logs archive and returns a reader object.

    Parameters
    ----------
    buffer : io.BytesIO
        The opened archive stream.
    filename : str
        The archive filename.
    password : str
        If applicable, the password required to open the archive.

    Returns
    -------
    stealer_parser.models.archive_wrapper.ArchiveWrapper or None

    Raises
    ------
    NotImplementedError
        If the ZIP compression method or the file extension is not handled.
    rarfile.Error
        If either unrar, unar or bdstar binary is not found.
    py7zr.exceptions.Bad7zFile
        If the file is not a 7-Zip file.
    FileNotFoundError, OSError, PermissionError
        If the archive file is not found or can't be read.

    """
    archive: RarFile | ZipFile | SevenZipFile

    match Path(filename).suffix:
        case ".rar":
            archive = RarFile(buffer)

        case ".zip":
            archive = ZipFile(buffer)

        case ".7z":
            archive = SevenZipFile(buffer, password=password)

        case other_ext:
            raise NotImplementedError(f"{other_ext} not handled.")

    return ArchiveWrapper(archive, filename=filename, password=password)

@inject
def main(
    db_exporter: PostgreSQLExporter = Provide[AppContainer.services.postgres_exporter],
    logger: VerboseLogger = Provide[AppContainer.logger],
    leak_processor: "LeakProcessor" = Provide[AppContainer.leak_processor],
    settings: Settings = Provide[AppContainer.config],
) -> None:
    """Program's entrypoint."""
    args: Namespace = parse_options("Parse infostealer logs archives.")

    archive: ArchiveWrapper | None = None
    leak: Leak | None = None

    try:
        with open(args.filename, "rb") as file_handle:
            with BytesIO(file_handle.read()) as buffer:
                archive = read_archive(buffer, args.filename, args.password)
                leak = leak_processor.process_leak(archive)

    except (
        FileNotFoundError,
        NotImplementedError,
        OSError,
        PermissionError,
    ) as err:
        logger.error(f"Failed reading {args.filename}: {err}")

    except RuntimeError as err:
        logger.error(f"Failed parsing {args.filename}: {err}")

    else:
        if leak:
            # Default: export to DB based on environment/config
            export_to_database(db_exporter=db_exporter, logger=logger, leak=leak, settings=settings)
            # Optional: also dump JSON if requested
            if getattr(args, "dump_json", None):
                from stealer_parser.helpers import dump_to_file
                dump_to_file(logger, args.dump_json, leak)

    finally:
        if archive:
            archive.close()

def export_to_database(
    db_exporter: PostgreSQLExporter,
    logger: VerboseLogger,
    leak: Leak,
    settings: Settings,
) -> None:
    """Export leak data to PostgreSQL database.
    
    Parameters
    ----------
    logger : VerboseLogger
        The logger instance.
    leak : Leak
        The parsed leak data.
    args : Namespace
        Command-line arguments.
    container : Container
        The dependency injection container.
    
    """
    try:
        # Test connection
        with db_exporter:
            if not db_exporter.test_connection():
                logger.error("Failed to establish database connection")
                return
            
            # Create tables if requested via settings
            if getattr(settings, "db_create_tables", False):
                logger.info("Creating database tables...")
                db_exporter.recreate_schema()
            
            # Export the leak data
            logger.info(f"Exporting {leak.filename} to database...")
            stats = db_exporter.export_leak(leak)
            
            logger.info(
                f"Database export completed successfully: "
                f"{stats['systems']} systems, {stats['credentials']} credentials, "
                f"{stats['cookies']} cookies, {stats.get('vaults', 0)} vaults, {stats.get('user_files', 0)} user_files exported"
            )
    
    except Exception as err:
        logger.error(f"Database export failed: {err}")
        logger.debug("Full error details:", exc_info=True)


if __name__ == "__main__":
    # Initialize DI container
    app_container = AppContainer()

    app_container.wire(modules=[__name__])
    # Initialize resources (e.g., DB pool)
    app_container.init_resources()
    try:
        # Resolve dependencies explicitly to avoid unresolved Provide objects
        logger = app_container.logger()
        leak_processor = app_container.leak_processor()
        db_exporter = app_container.services.postgres_exporter()
        settings = app_container.config()
        main(logger=logger, leak_processor=leak_processor, db_exporter=db_exporter, settings=settings)
    finally:
        # Ensure resources are cleaned up
        app_container.shutdown_resources()
