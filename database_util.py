from pymongo import MongoClient
from consul_util import get_config_value
from logger_util import get_logger

logger = get_logger()
try:
    client = MongoClient(get_config_value('DB_IP').decode(encoding="utf-8"), int(get_config_value('DB_PORT')))
    logger.info("Database connection establishes!!!!!!")
except Exception as e:
    logger.fatal(str(e))


def get_master_collection():
    db = client.botengine.master
    return db


def get_service_collection():
    db = client.botengine.services
    return db


def get_account_history_collection():
    db = client.botengine.account_history
    return db

