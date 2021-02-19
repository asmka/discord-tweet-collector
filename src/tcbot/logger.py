import logging

logging.basicConfig(level=logging.ERROR, format="%(threadName)s: %(message)s")
logger = logging.getLogger(__name__)
