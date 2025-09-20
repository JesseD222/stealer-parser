"""Helper functions."""
from argparse import ArgumentParser, Namespace
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from json import JSONEncoder, dumps
from pathlib import Path
from typing import Any

import coloredlogs
from verboselogs import VerboseLogger


class EnhancedJSONEncoder(JSONEncoder):
    """Enhanced JSON encoder for specific classes."""

    def default(self, o: Any) -> Any:  # type: ignore[override]
        """Handle custom types JSON serialization."""
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, set):
            return list(o)
        return super().default(o)


def dump_to_file(
    logger: VerboseLogger, filename: str, content: str | Any
) -> None:
    """Save data to local file.

    Parameters
    ----------
    logger : verboselogs.VerboseLogger
        The program's logger.
    filebame : str
        The file to write to.
    content : str or Any
        The data to write.

    """
    filepath = Path(filename)

    try:
        if not filepath.parent.exists():
            filepath.parent.mkdir(parents=True)

        if not isinstance(content, str):
            filepath.write_text(
                dumps(
                    content,
                    ensure_ascii=False,
                    cls=EnhancedJSONEncoder,
                    indent=4,
                )
            )
        else:
            filepath.write_text(content)

    except (FileNotFoundError, OSError, PermissionError, ValueError) as err:
        logger.error(f"Failed to write file to '{str(filepath)}': {err}")

    else:
        logger.info(f"Successfully wrote '{str(filepath)}'.")


def parse_options(description: str) -> Namespace:
    """Parse command-line arguments.

    Parameters
    ----------
    description : str
        The program's description.

    Returns
    -------
    argparse.Namespace
        Parsed command-line arguments as an object.

    """
    parser = ArgumentParser(description=description)

    parser.add_argument(
        "filename",
        type=str,
        help="the archive to process (handled extensions: .rar, .zip, .7z)",
    )
    parser.add_argument(
        "-p",
        "--password",
        metavar="ARCHIVE_PASSWORD",
        type=str,
        default=None,
        help="the archive's password if required",
    )
    parser.add_argument(
        "--dump-json",
        metavar="FILENAME.json",
        type=str,
        default=None,
        help="also write parsed output to a JSON file",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase logs output verbosity (default: info, -v: verbose, "
        "-vv: debug, -vvv: spam)",
    )

    args: Namespace = parser.parse_args()

    # No validation needed: DB export is default; JSON dump is optional

    return args


def init_logger(
    name: str,
    verbosity_level: str,
    formatting: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> VerboseLogger:
    """Initialize the program's logger.

    Parameters
    ----------
    name : str
        The logger's name.
    verbosity_level : int
        Verbosity log level.
    formatting : str, optional
        The log format.

    Returns
    -------
    verboselogs.VerboseLogger
        The logger.

    """
    levels: list[str] = ["INFO", "VERBOSE", "DEBUG", "SPAM"]
    logger = VerboseLogger(name)

    coloredlogs.install(
        logger=logger,
        level=10,
        fmt=formatting,
        isatty=True,
    )

    return logger
