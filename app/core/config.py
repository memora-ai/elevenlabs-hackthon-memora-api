from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Set empty defaults - values must be provided by .env
    DATABASE_URL: str = ""
    API_V1_STR: str = "/api/v1"  # This can keep a default
    PROJECT_NAME: str = "FastAPI Project"  # This can keep a default

    # Azure OpenAI Settings
    AZURE_DEPLOYMENT_NAME: str = ""
    AZURE_OPENAI_API_VERSION: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""

    # Auth0 Settings
    AUTH0_DOMAIN: str = ""
    API_AUDIENCE: str = ""
    ALGORITHMS: str = "RS256"  # This can keep a default

    ELEVENLABS_APIKEY: str = ""

    FALAI_APIKEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True  # Added to ensure exact matching of env variables

settings = Settings() 