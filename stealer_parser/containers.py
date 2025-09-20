"""Dependency injection containers for the stealer-parser application."""

from __future__ import annotations
from typing import Annotated

from dependency_injector import containers, providers
from verboselogs import VerboseLogger

from stealer_parser.config import Settings
from stealer_parser.database.dao.base import (
    CookiesDAO,
    CredentialsDAO,
    LeaksDAO,
    SystemsDAO,
)
from stealer_parser.database.dao.credential_cookie import CredentialCookieDAO
from stealer_parser.database.dao.vault import VaultDAO
from stealer_parser.database.dao.user_file import UserFilesDAO
from stealer_parser.database.postgres import PostgreSQLExporter
from stealer_parser.services.credential_cookie_matcher import CredentialCookieMatcher
from stealer_parser.services.leak_processor import LeakProcessor
from stealer_parser.parsing.registry import ParserRegistry
from stealer_parser.helpers import init_logger
from pathlib import Path

# New imports for definition-driven parser
from stealer_parser.parsing.definition_store import DefinitionStore
from stealer_parser.parsing.factory import StrategyRegistry, ParserFactory, Chunker, Extractor, Transformer
from stealer_parser.parsing.strategies.defaults import (
    RegexSeparatorChunker,
    KVHeaderExtractor,
    AliasGroupingTransformer,
    LineChunker,
    DelimitedLineExtractor,
    FullFileChunker,
    VaultExtractor,
    VaultTransformer,
)


try:
    import psycopg2
    import psycopg2.pool
except ImportError:  # pragma: no cover - optional dependency
    psycopg2 = None


class DatabaseContainer(containers.DeclarativeContainer):
    """Container for database-related components."""

    config = providers.Dependency(instance_of=Settings)
    logger = providers.Dependency(instance_of=VerboseLogger)

    db_pool = providers.Singleton(
        psycopg2.pool.SimpleConnectionPool,
        minconn=1,
        maxconn=10,
        host=config.provided.db_host,
        port=config.provided.db_port,
        dbname=config.provided.db_name,
        user=config.provided.db_user,
        password=config.provided.db_password,
    ) if psycopg2 else providers.Object(None)

    leaks_dao = providers.Factory(LeaksDAO, db_pool=db_pool, logger=logger)
    systems_dao = providers.Factory(SystemsDAO, db_pool=db_pool, logger=logger)
    credentials_dao = providers.Factory(CredentialsDAO, db_pool=db_pool, logger=logger)
    cookies_dao = providers.Factory(CookiesDAO, db_pool=db_pool, logger=logger)
    vaults_dao = providers.Factory(VaultDAO, db_pool=db_pool, logger=logger)
    user_files_dao = providers.Factory(UserFilesDAO, db_pool=db_pool, logger=logger)
    credential_cookie_dao = providers.Factory(
        CredentialCookieDAO, db_pool=db_pool, logger=logger
    )


class ServicesContainer(containers.DeclarativeContainer):
    """Container for application services."""

    config = providers.Dependency(instance_of=Settings)
    logger = providers.Dependency(instance_of=VerboseLogger)
    database = providers.DependenciesContainer()

    postgres_exporter = providers.Factory(
        PostgreSQLExporter,
        db_pool=database.db_pool,
        leaks_dao=database.leaks_dao,
        systems_dao=database.systems_dao,
        credentials_dao=database.credentials_dao,
        cookies_dao=database.cookies_dao,
        vaults_dao=database.vaults_dao,
        user_files_dao=database.user_files_dao,
        logger=logger,
    )

    credential_cookie_matcher = providers.Factory(
        CredentialCookieMatcher,
        credential_cookie_dao=database.credential_cookie_dao,
        logger=logger,
    )


class AppContainer(containers.DeclarativeContainer):
    """Main application container."""

    config = providers.Singleton(Settings)
    logger = providers.Singleton(init_logger, "stealer_parser",
                                 "verbosity_level=DEBUG")

    database = providers.Container(
        DatabaseContainer,
        config=config,
        logger=logger,
    )

    services = providers.Container(
        ServicesContainer,
        config=config,
        logger=logger,
        database=database,
    )

    # Strategy registry and parser factory
    strategy_registry = providers.Singleton(StrategyRegistry)
    parser_factory = providers.Singleton(ParserFactory, strategies=strategy_registry)

    # Definition store: directory configurable via settings
    definition_store = providers.Singleton(
        DefinitionStore,
        base_dirs=providers.Callable(lambda cfg: [Path(p) for p in getattr(cfg, "record_definitions_dirs", ["record_definitions"])], config),
    )

    # Ensure default strategies are registered during init_resources()
    strategies_initializer = providers.Resource(
        lambda reg: (
            reg.register(Chunker, RegexSeparatorChunker()),
            reg.register(Extractor, KVHeaderExtractor()),
            reg.register(Transformer, AliasGroupingTransformer()),
            reg.register(Chunker, LineChunker()),
            reg.register(Extractor, DelimitedLineExtractor()),
            reg.register(Chunker, FullFileChunker()),
            reg.register(Extractor, VaultExtractor()),
            reg.register(Transformer, VaultTransformer()),
        ),
        strategy_registry,
    )

    parser_registry = providers.Singleton(
        ParserRegistry,
        logger=logger,
        definition_store=definition_store,
        parser_factory=parser_factory,
    )

    leak_processor = providers.Factory(
        LeakProcessor,
        parser_registry=parser_registry,
        logger=logger,
    )
