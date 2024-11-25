from dataclasses import dataclass
import os

@dataclass
class Config:
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
    REDIS_EXPIRE_TIME = int(os.getenv('REDIS_EXPIRE_TIME', 3600))
    RQ_QUEUE_NAME = os.getenv('RQ_QUEUE_NAME', 'exhibition')
    MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
    MONGODB_HOST = os.getenv('MONGODB_HOST', 'mongodb://172.18.0.1:27017')
    MONGODB_DB = os.getenv('MONGODB_DB', 'SeeM')