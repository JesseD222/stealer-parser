"""Centralized configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Defines application settings, loaded from environment variables or .env file.
    
    Attributes
    ----------
    db_host : str
        PostgreSQL server hostname.
    db_port : int
        PostgreSQL server port.
    db_name : str
        Database name to connect to.
    db_user : str
        Database username.
    db_password : str
        Database password.
    """
    
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "derp"
    db_user: str = "derp"
    db_password: str = "disforderp"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

# Create a single instance of settings to be used throughout the application
settings = Settings()
