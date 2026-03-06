import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
_log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, _log_level, logging.INFO))
logger = logging.getLogger(__name__)


def get_required_env(name: str) -> str:
    """Get required environment variable or exit with clear error."""
    value = os.environ.get(name)
    if not value:
        logger.error(f"Required environment variable '{name}' is not set.")
        sys.exit(1)
    return value


# Validate environment variables
SUPABASE_URL = get_required_env("SUPABASE_URL")
SUPABASE_KEY = get_required_env("SUPABASE_KEY")
get_required_env("OPENAI_API_KEY")  # langchain_openai reads this automatically

# Optional: Cohere API key for reranking (gracefully degrades if not set)
COHERE_API_KEY = os.environ.get("COHERE_API_KEY")

# Optional: Redis URL for distributed rate limiting
REDIS_URL = os.environ.get("REDIS_URL")

# Optional: LangGraph Postgres checkpointer connection
LANGGRAPH_DB_URL = os.environ.get("LANGGRAPH_DB_URL")

# Optional: Sentry DSN for error tracking
SENTRY_DSN = os.environ.get("SENTRY_DSN")

# Storage buckets
DOCUMENTS_BUCKET = os.environ.get("DOCUMENTS_BUCKET", "documents")
BRIEF_PDF_BUCKET = os.environ.get("BRIEF_PDF_BUCKET", "briefs")

# Retention policy default (days)
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "90"))

# Supabase JWT secret for auth token verification
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")
if not SUPABASE_JWT_SECRET:
    logger.warning("SUPABASE_JWT_SECRET is not set — auth endpoints will reject all requests")

# CORS configuration (comma-separated list of allowed origins)
_cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
CORS_ORIGINS = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]

# Optional: AustLII proxy for deployed environments where AustLII blocks direct access
AUSTLII_PROXY_URL = os.environ.get("AUSTLII_PROXY_URL")
AUSTLII_PROXY_SECRET = os.environ.get("AUSTLII_PROXY_SECRET")
