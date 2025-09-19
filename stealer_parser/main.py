"""Infostealer logs parser."""
from argparse import Namespace
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from py7zr import SevenZipFile
from rarfile import RarFile
from verboselogs import VerboseLogger
from stealer_parser.containers import Container
from stealer_parser.helpers import dump_to_file, init_logger, parse_options
from stealer_parser.models import ArchiveWrapper, Leak
from stealer_parser.processing import process_archive

# Import database components with fallback
try:
    from stealer_parser.database import PostgreSQLExporter
    DATABASE_AVAILABLE = True
except ImportError:
    PostgreSQLExporter = None  # type: ignore
    DATABASE_AVAILABLE = False


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


def main() -> None:
    """Program's entrypoint."""
    args: Namespace = parse_options("Parse infostealer logs archives.")

    
    # Initialize DI container and override config with CLI args
    container = Container()
    container.config.db_host.override(args.db_host)
    container.config.db_port.override(args.db_port)
    container.config.db_name.override(args.db_name)
    container.config.db_user.override(args.db_user)
    container.config.db_password.override(args.db_password)

    logger = container.logger()
    
    archive: ArchiveWrapper | None = None

    try:
        leak = Leak(filename=args.filename)

        with open(args.filename, "rb") as file_handle:
            with BytesIO(file_handle.read()) as buffer:
                archive = read_archive(buffer, args.filename, args.password)
                process_archive(logger, leak, archive)

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
        # Export data based on user preference
        if args.db_export:
            export_to_database(logger, leak, args, container)
        else:
            dump_to_file(logger, args.outfile, leak)

    finally:
        if archive:
            archive.close()


def validate_database_config(args: Namespace) -> bool:
    """Validate database configuration parameters.
    
    Parameters
    ----------
    args : Namespace
        Command-line arguments with database parameters.
    
    Returns
    -------
    bool
        True if configuration is valid, False otherwise.
    
    """
    required_fields = ['db_host', 'db_port', 'db_name', 'db_user']
    
    for field in required_fields:
        if not hasattr(args, field) or getattr(args, field) is None:
            return False
    
    # Validate port number
    if not isinstance(args.db_port, int) or args.db_port <= 0 or args.db_port > 65535:
        return False
    
    return True


def export_to_database(logger: VerboseLogger, leak: Leak, args: Namespace, container: Container) -> None:
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
    if not DATABASE_AVAILABLE:
        logger.error(
            "Database export requested but psycopg2 is not installed. "
            "Install it with: pip install psycopg2-binary"
        )
        return
    
    try:
        # Get database exporter from the container
        db_exporter = container.postgres_exporter()
        
        # Test connection
        with db_exporter:
            if not db_exporter.test_connection():
                logger.error("Failed to establish database connection")
                return
            
            # Create tables if requested
            if args.db_create_tables:
                logger.info("Creating database tables...")
                db_exporter.create_tables()
            
            # Export the leak data
            logger.info(f"Exporting {args.filename} to database...")
            stats = db_exporter.export_leak(leak)
            
            logger.info(
                f"Database export completed successfully: "
                f"{stats['systems']} systems, {stats['credentials']} credentials, "
                f"{stats['cookies']} cookies exported"
            )
    
    except Exception as err:
        logger.error(f"Database export failed: {err}")
        logger.debug("Full error details:", exc_info=True)


if __name__ == "__main__":
    main()
