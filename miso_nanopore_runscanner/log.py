import logging

from miso_nanopore_runscanner.config import LOGFORMAT

logger = logging.getLogger(__name__)


def init_logging():
    logging.basicConfig(level=logging.INFO, format=LOGFORMAT)
