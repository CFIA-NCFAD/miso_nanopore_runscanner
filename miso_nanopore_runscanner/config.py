import os

LOGFORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
HOST: str = os.environ.get("HOST", "0.0.0.0")
PORT: int = int(os.environ.get("PORT", 8000))
DEBUG: bool = os.environ.get("DEBUG", "False").lower() == "true"
BASEDIR = os.environ.get("NANOPORE_BASEDIR", "/Zarls/GridION-data")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///miso_nanopore_runscanner.db")
PARSE_SEQSUMMARY = os.environ.get("PARSE_SEQSUMMARY", "False").lower() == "true"
