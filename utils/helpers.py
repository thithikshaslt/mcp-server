from bson import ObjectId
from .db_utils import get_mongo_client
from .constants import DEFAULT_DATABASE, PROFILE_COLLECTION

def get_email_by_name(name: str) -> str | None:
    """
    Resolves and returns the email address associated with the given user's name.
    """
    client = get_mongo_client()
    try:
        db = client[DEFAULT_DATABASE]
        profile = db[PROFILE_COLLECTION].find_one({
            "name": {"$regex": f"^{name.strip()}$", "$options": "i"}
        })
        if not profile:
            return None
        return profile.get("email", "").lower()
    finally:
        client.close()

def serialize_doc(doc: dict) -> dict:
    """Recursively convert ObjectIds to strings"""
    if isinstance(doc, dict):
        return {
            key: str(value) if isinstance(value, ObjectId) else serialize_doc(value)
            if isinstance(value, dict) else [
                serialize_doc(item) if isinstance(item, dict) else item
                for item in value
            ] if isinstance(value, list) else value
            for key, value in doc.items()
        }
    return doc

