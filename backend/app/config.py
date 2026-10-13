from pydantic_settings import BaseSettings


class Settings(BaseSettings):
	database_url: str = "postgresql+psycopg://poke:poke@localhost:5432/poke"
	redis_url: str = "redis://localhost:6379/0"
	s3_endpoint: str = "http://localhost:9000"
	s3_key: str = "minio"
	s3_secret: str = "minio123"
	s3_bucket: str = "cards"
	scraper_user_agent: str = "PokeScanner/0.1"
	tcgplayer_public_key: str | None = None
	tcgplayer_private_key: str | None = None
	tcgplayer_api_base: str = "https://api.tcgplayer.com"
	tcgplayer_api_version: str = "v1.39.0"
	open_tcg_enabled: bool = False
	open_tcg_base: str = "https://openapi.tcgtracking.com"
	open_tcg_api_version: str = "v1"
	open_tcg_game_id: int = 1
	open_tcg_api_key: str | None = None
	open_tcg_timeout_seconds: float = 30.0

	class Config:
		env_file = ".env"


settings = Settings()
