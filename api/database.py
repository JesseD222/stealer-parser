"""
High-performance database layer for stealer parser with async support.
Designed to handle millions of records efficiently.
"""
import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import asyncpg
import aiosqlite
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, Boolean, Float, Index
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import text
import redis.asyncio as redis

# Configuration
DATABASE_URL = "sqlite+aiosqlite:///stealer_parser.db"
REDIS_URL = "redis://localhost:6379"
POSTGRES_URL = "postgresql+asyncpg://user:password@localhost/stealer_parser"

# Database models
Base = declarative_base()


class ParseSession(Base):
    """Represents a parsing session for an uploaded archive."""
    __tablename__ = "parse_sessions"

    id = Column(String, primary_key=True)  # UUID
    filename = Column(String, nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow, index=True)
    processing_start = Column(DateTime)
    processing_end = Column(DateTime)
    status = Column(String, default="pending", index=True)  # pending, processing, completed, failed
    progress = Column(Float, default=0.0)
    current_step = Column(String)
    error_message = Column(Text)
    total_systems = Column(Integer, default=0)
    total_credentials = Column(Integer, default=0)
    total_cookies = Column(Integer, default=0)
    metadata_ = Column(JSONB)  # PostgreSQL JSONB, fallback to Text for SQLite

    __table_args__ = (
        Index("idx_sessions_status_time", "status", "upload_time"),
        Index("idx_sessions_filename_time", "filename", "upload_time"),
    )


class CompromisedSystem(Base):
    """Represents a compromised system found in the archive."""
    __tablename__ = "compromised_systems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    machine_id = Column(String, index=True)
    computer_name = Column(String, index=True)
    hardware_id = Column(String)
    machine_user = Column(String, index=True)
    ip_address = Column(String, index=True)
    country = Column(String, index=True)
    log_date = Column(DateTime, index=True)
    stealer_name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_systems_session_country", "session_id", "country"),
        Index("idx_systems_stealer_date", "stealer_name", "log_date"),
        Index("idx_systems_ip_country", "ip_address", "country"),
    )


class ExtractedCredential(Base):
    """Represents extracted credentials from compromised systems."""
    __tablename__ = "extracted_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    system_id = Column(Integer, nullable=False, index=True)
    software = Column(String, index=True)
    host = Column(String, index=True)
    domain = Column(String, index=True)
    username = Column(String, index=True)
    password_hash = Column(String)  # Store hash for security, not plaintext
    password_strength = Column(String, index=True)  # weak, medium, strong
    email_domain = Column(String, index=True)
    local_part = Column(String)
    filepath = Column(String)
    stealer_name = Column(String, index=True)
    risk_level = Column(String, index=True)  # low, medium, high, critical
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_creds_session_domain", "session_id", "domain"),
        Index("idx_creds_stealer_risk", "stealer_name", "risk_level"),
        Index("idx_creds_domain_risk", "domain", "risk_level"),
        Index("idx_creds_software_domain", "software", "domain"),
    )


class ExtractedCookie(Base):
    """Represents browser cookies from compromised systems."""
    __tablename__ = "extracted_cookies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    system_id = Column(Integer, nullable=False, index=True)
    domain = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    value_hash = Column(String)  # Hash of cookie value for security
    browser = Column(String, index=True)
    secure = Column(Boolean, index=True)
    http_only = Column(Boolean, index=True)
    expiry = Column(DateTime, index=True)
    filepath = Column(String)
    stealer_name = Column(String, index=True)
    is_session_token = Column(Boolean, default=False, index=True)
    risk_level = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_cookies_session_domain", "session_id", "domain"),
        Index("idx_cookies_domain_browser", "domain", "browser"),
        Index("idx_cookies_stealer_risk", "stealer_name", "risk_level"),
        Index("idx_cookies_expiry_secure", "expiry", "secure"),
    )


class DomainAnalysis(Base):
    """Aggregated analysis of compromised domains."""
    __tablename__ = "domain_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String, nullable=False, unique=True, index=True)
    total_credentials = Column(Integer, default=0)
    total_cookies = Column(Integer, default=0)
    total_systems = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0, index=True)
    category = Column(String, index=True)  # social, email, financial, cloud, etc.
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    stealer_variants = Column(JSONB)  # List of stealer types
    countries = Column(JSONB)  # List of affected countries
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_domain_risk_category", "risk_score", "category"),
        Index("idx_domain_last_seen", "last_seen"),
    )


class ProcessingStats(Base):
    """System-wide processing statistics and metrics."""
    __tablename__ = "processing_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    total_sessions = Column(Integer, default=0)
    total_archives_processed = Column(Integer, default=0)
    total_credentials_extracted = Column(Integer, default=0)
    total_cookies_extracted = Column(Integer, default=0)
    total_systems_compromised = Column(Integer, default=0)
    unique_domains = Column(Integer, default=0)
    unique_stealers = Column(Integer, default=0)
    avg_processing_time = Column(Float, default=0.0)
    peak_memory_usage = Column(Float, default=0.0)
    stats_data = Column(JSONB)  # Additional metrics

    __table_args__ = (
        Index("idx_stats_date", "date"),
    )


class DatabaseManager:
    """High-performance async database manager."""

    def __init__(self, database_url: str = DATABASE_URL, redis_url: str = REDIS_URL):
        self.database_url = database_url
        self.redis_url = redis_url
        self.engine = None
        self.async_session = None
        self.redis_pool = None

    async def init_database(self):
        """Initialize database connections and create tables."""
        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=20,  # Connection pool size
            max_overflow=30,  # Additional connections
            pool_pre_ping=True,  # Validate connections
            pool_recycle=3600,  # Recycle connections every hour
        )
        
        # Create session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Initialize Redis
        self.redis_pool = redis.ConnectionPool.from_url(self.redis_url, decode_responses=True)
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Enable WAL mode for SQLite
        if "sqlite" in self.database_url.lower():
            async with self.engine.begin() as conn:
                await conn.execute(text("PRAGMA journal_mode=WAL"))
                await conn.execute(text("PRAGMA synchronous=NORMAL"))
                await conn.execute(text("PRAGMA cache_size=1000000"))
                await conn.execute(text("PRAGMA temp_store=MEMORY"))
                await conn.execute(text("PRAGMA mmap_size=268435456"))  # 256MB

    @asynccontextmanager
    async def get_session(self):
        """Get async database session with proper error handling."""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()

    @asynccontextmanager
    async def get_redis(self):
        """Get Redis connection."""
        redis_conn = redis.Redis(connection_pool=self.redis_pool)
        try:
            yield redis_conn
        finally:
            await redis_conn.aclose()

    async def create_parse_session(
        self, 
        session_id: str, 
        filename: str, 
        file_size: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ParseSession:
        """Create a new parse session."""
        async with self.get_session() as session:
            parse_session = ParseSession(
                id=session_id,
                filename=filename,
                file_size=file_size,
                metadata_=metadata or {}
            )
            session.add(parse_session)
            await session.flush()
            return parse_session

    async def update_session_status(
        self, 
        session_id: str, 
        status: str, 
        progress: float = None,
        current_step: str = None,
        error_message: str = None
    ):
        """Update parse session status."""
        async with self.get_session() as session:
            result = await session.execute(
                text("UPDATE parse_sessions SET status = :status, progress = :progress, "
                     "current_step = :current_step, error_message = :error_message, "
                     "processing_start = CASE WHEN status = 'processing' AND processing_start IS NULL "
                     "THEN datetime('now') ELSE processing_start END, "
                     "processing_end = CASE WHEN status IN ('completed', 'failed') "
                     "THEN datetime('now') ELSE processing_end END "
                     "WHERE id = :session_id"),
                {
                    "status": status,
                    "progress": progress,
                    "current_step": current_step,
                    "error_message": error_message,
                    "session_id": session_id
                }
            )

    async def bulk_insert_credentials(
        self, 
        session_id: str, 
        system_id: int,
        credentials: List[Dict[str, Any]]
    ):
        """Bulk insert credentials for high performance."""
        if not credentials:
            return

        async with self.get_session() as session:
            # Prepare bulk insert data
            insert_data = []
            for cred in credentials:
                insert_data.append({
                    'session_id': session_id,
                    'system_id': system_id,
                    'software': cred.get('software'),
                    'host': cred.get('host'),
                    'domain': cred.get('domain'),
                    'username': cred.get('username'),
                    'password_hash': self._hash_sensitive_data(cred.get('password')),
                    'password_strength': self._assess_password_strength(cred.get('password')),
                    'email_domain': cred.get('email_domain'),
                    'local_part': cred.get('local_part'),
                    'filepath': cred.get('filepath'),
                    'stealer_name': cred.get('stealer_name'),
                    'risk_level': self._assess_credential_risk(cred.get('domain')),
                    'created_at': datetime.utcnow()
                })

            # Bulk insert using raw SQL for performance
            await session.execute(
                text("""
                    INSERT INTO extracted_credentials 
                    (session_id, system_id, software, host, domain, username, password_hash, 
                     password_strength, email_domain, local_part, filepath, stealer_name, 
                     risk_level, created_at)
                    VALUES (:session_id, :system_id, :software, :host, :domain, :username, 
                            :password_hash, :password_strength, :email_domain, :local_part, 
                            :filepath, :stealer_name, :risk_level, :created_at)
                """),
                insert_data
            )

    async def bulk_insert_cookies(
        self, 
        session_id: str, 
        system_id: int,
        cookies: List[Dict[str, Any]]
    ):
        """Bulk insert cookies for high performance."""
        if not cookies:
            return

        async with self.get_session() as session:
            insert_data = []
            for cookie in cookies:
                insert_data.append({
                    'session_id': session_id,
                    'system_id': system_id,
                    'domain': cookie.get('domain'),
                    'name': cookie.get('name'),
                    'value_hash': self._hash_sensitive_data(cookie.get('value')),
                    'browser': cookie.get('browser'),
                    'secure': cookie.get('secure', False),
                    'http_only': cookie.get('http_only', False),
                    'expiry': self._parse_datetime(cookie.get('expiry')),
                    'filepath': cookie.get('filepath'),
                    'stealer_name': cookie.get('stealer_name'),
                    'is_session_token': self._is_session_token(cookie.get('name')),
                    'risk_level': self._assess_cookie_risk(cookie.get('domain'), cookie.get('name')),
                    'created_at': datetime.utcnow()
                })

            await session.execute(
                text("""
                    INSERT INTO extracted_cookies 
                    (session_id, system_id, domain, name, value_hash, browser, secure, 
                     http_only, expiry, filepath, stealer_name, is_session_token, 
                     risk_level, created_at)
                    VALUES (:session_id, :system_id, :domain, :name, :value_hash, :browser, 
                            :secure, :http_only, :expiry, :filepath, :stealer_name, 
                            :is_session_token, :risk_level, :created_at)
                """),
                insert_data
            )

    async def get_session_results(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive results for a parse session."""
        async with self.get_session() as session:
            # Get session info
            session_result = await session.execute(
                text("SELECT * FROM parse_sessions WHERE id = :session_id"),
                {"session_id": session_id}
            )
            session_data = session_result.fetchone()
            
            if not session_data:
                return None

            # Get systems
            systems_result = await session.execute(
                text("SELECT * FROM compromised_systems WHERE session_id = :session_id"),
                {"session_id": session_id}
            )
            systems = systems_result.fetchall()

            # Get credentials
            creds_result = await session.execute(
                text("SELECT * FROM extracted_credentials WHERE session_id = :session_id"),
                {"session_id": session_id}
            )
            credentials = creds_result.fetchall()

            # Get cookies
            cookies_result = await session.execute(
                text("SELECT * FROM extracted_cookies WHERE session_id = :session_id"),
                {"session_id": session_id}
            )
            cookies = cookies_result.fetchall()

            return {
                "session": dict(session_data._mapping),
                "systems": [dict(row._mapping) for row in systems],
                "credentials": [dict(row._mapping) for row in credentials],
                "cookies": [dict(row._mapping) for row in cookies]
            }

    async def get_analytics_summary(self, limit: int = 1000) -> Dict[str, Any]:
        """Get analytics summary with efficient queries."""
        async with self.get_session() as session:
            # Domain statistics
            domain_stats = await session.execute(
                text("""
                    SELECT domain, COUNT(*) as credential_count, 
                           AVG(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) as risk_ratio
                    FROM extracted_credentials 
                    WHERE domain IS NOT NULL
                    GROUP BY domain 
                    ORDER BY credential_count DESC 
                    LIMIT :limit
                """),
                {"limit": limit}
            )

            # Country distribution
            country_stats = await session.execute(
                text("""
                    SELECT country, COUNT(*) as system_count
                    FROM compromised_systems 
                    WHERE country IS NOT NULL
                    GROUP BY country 
                    ORDER BY system_count DESC
                """)
            )

            # Stealer statistics
            stealer_stats = await session.execute(
                text("""
                    SELECT stealer_name, COUNT(DISTINCT session_id) as session_count,
                           COUNT(*) as total_credentials
                    FROM extracted_credentials 
                    WHERE stealer_name IS NOT NULL
                    GROUP BY stealer_name 
                    ORDER BY total_credentials DESC
                """)
            )

            return {
                "top_domains": [dict(row._mapping) for row in domain_stats.fetchall()],
                "country_distribution": [dict(row._mapping) for row in country_stats.fetchall()],
                "stealer_statistics": [dict(row._mapping) for row in stealer_stats.fetchall()]
            }

    def _hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for security."""
        if not data:
            return None
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()[:16]  # First 16 chars for indexing

    def _assess_password_strength(self, password: str) -> str:
        """Assess password strength."""
        if not password:
            return "unknown"
        
        if len(password) < 8:
            return "weak"
        elif len(password) < 12 or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
            return "medium"
        else:
            return "strong"

    def _assess_credential_risk(self, domain: str) -> str:
        """Assess credential risk level based on domain."""
        if not domain:
            return "low"
        
        high_risk = ["gmail.com", "outlook.com", "paypal.com", "amazon.com", "apple.com"]
        medium_risk = ["facebook.com", "twitter.com", "linkedin.com", "microsoft.com"]
        
        domain_lower = domain.lower()
        
        if any(risk_domain in domain_lower for risk_domain in high_risk):
            return "high"
        elif any(risk_domain in domain_lower for risk_domain in medium_risk):
            return "medium"
        else:
            return "low"

    def _assess_cookie_risk(self, domain: str, name: str) -> str:
        """Assess cookie risk level."""
        if not domain or not name:
            return "low"
        
        if self._is_session_token(name):
            return "high"
        elif "auth" in name.lower() or "session" in name.lower():
            return "medium"
        else:
            return "low"

    def _is_session_token(self, cookie_name: str) -> bool:
        """Check if cookie is likely a session token."""
        if not cookie_name:
            return False
        
        session_indicators = ["session", "token", "auth", "login", "sid", "ssid"]
        name_lower = cookie_name.lower()
        
        return any(indicator in name_lower for indicator in session_indicators)

    def _parse_datetime(self, dt_string: str) -> Optional[datetime]:
        """Parse datetime string safely."""
        if not dt_string:
            return None
        
        try:
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except:
            return None

    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
        if self.redis_pool:
            await self.redis_pool.disconnect()


# Global database manager instance
db_manager = DatabaseManager()