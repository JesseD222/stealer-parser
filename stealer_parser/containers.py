"""Dependency injection containers for the stealer-parser application."""

from dependency_injector import containers, providers
from psycopg2.pool import SimpleConnectionPool

from stealer_parser.config import Settings
from verboselogs import VerboseLogger

from .database.postgres import PostgreSQLExporter
from .credential_cookie_matcher import CredentialCookieMatcher


class Container(containers.DeclarativeContainer):
    """Main DI container for the application."""
    
    # Configuration provider
    config = providers.Configuration(pydantic_settings=[Settings()])
    
    logger = providers.Singleton(
        VerboseLogger,
        name="StealerParser",
        verbosity_level=1,  # Default verbosity level; can be overridden
    )

    # Database connection pool provider
    db_pool = providers.Singleton(
        SimpleConnectionPool,
        minconn=1,
        maxconn=10,
        host=config.provided['db_host'],
        port=config.provided['db_port'],
        database=config.provided['db_name'],
        user=config.provided['db_user'],
        password=config.provided['db_password'],
    )
    
    # Service providers
    postgres_exporter = providers.Factory(
        PostgreSQLExporter,
        db_pool=db_pool,
    )
    
    credential_cookie_matcher = providers.Factory(
        CredentialCookieMatcher,
        db_pool=db_pool,
    )

# Create a single container instance to be used by the application
container = Container()
