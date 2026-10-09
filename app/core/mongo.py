# MongoDB connection setup, used for storing raw page-text snapshots.
from pymongo import MongoClient

from app.core.config import settings

# MongoClient connects lazily - no actual network call happens until we query/insert
mongo_client = MongoClient(
    settings.mongo_url, serverSelectionTimeoutMS=3000, tz_aware=True
)
mongo_db = mongo_client[settings.mongo_db_name]

# Collection holding one document per (domain, check) with the extracted page text
snapshots_collection = mongo_db["snapshots"]


def ensure_indexes():
    snapshots_collection.create_index([("domain_id", 1), ("last_seen_at", -1)])
    snapshots_collection.create_index("check_ids")
    snapshots_collection.create_index(
        "last_seen_at",
        expireAfterSeconds=settings.snapshot_ttl_days * 24 * 60 * 60,
    )


def ensure_schema_validator():
    mongo_db.command(
        {
            "collMod": "snapshots",
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": [
                        "domain_id",
                        "checked_at",
                        "text_content",
                        "last_seen_at",
                        "content_hash",
                        "seen_count",
                    ],
                    "properties": {
                        "domain_id": {"bsonType": "int"},
                        "checked_at": {"bsonType": "date"},
                        "text_content": {"bsonType": "string"},
                        "last_seen_at": {"bsonType": "date"},
                        "content_hash": {"bsonType": "string"},
                        "seen_count": {"bsonType": "int"},
                    },
                }
            },
        }
    )
