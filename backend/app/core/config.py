from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "WorkspaceAI"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL Connection Credentials (No fallbacks—must be in .env)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    #Gemini LLM creds:
    GEMINI_API_KEY: str
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768
    LLM_MODEL: str = "gemini-3.6-flash"

    # AWS / S3 credentials. Accept both S3_* and AWS_* names for compatibility.
    S3_ENDPOINT_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_ENDPOINT_URL", "AWS_ENDPOINT_URL"),
    )
    S3_ACCESS_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_ACCESS_KEY", "AWS_ACCESS_KEY"),
    )
    S3_SECRET_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_SECRET_KEY", "AWS_SECRET_KEY"),
    )
    S3_BUCKET_NAME: str = Field(
        default="workspace-docs-allan-dev",
        validation_alias=AliasChoices("S3_BUCKET_NAME", "AWS_S3_BUCKET_NAME"),
    )
    S3_REGION: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("S3_REGION", "AWS_REGION"),
    )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Constructs the asyncpg connection string."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # JWT Security Configuration (No fallbacks—must be in .env)
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()