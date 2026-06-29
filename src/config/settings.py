import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./data/processed/scrapper.db"
    )
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
    # Meta Ads Config
    META_ADS_API_URL: str = os.getenv(
        "META_ADS_API_URL", "https://graph.facebook.com/v19.0/ads_archive"
    )
    META_TIMEOUT_SECONDS: int = int(os.getenv("META_TIMEOUT_SECONDS", "30"))
    META_USER_AGENT: str = os.getenv("META_USER_AGENT", "MetaAdsScrapper/1.0")


settings = Settings()
