import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import config

# Global variables for MongoDB Client and Database
db_client = None
db = None

def init_db(mongo_uri: str = None):
    """Initializes the async MongoDB client."""
    global db_client, db
    uri = mongo_uri or config.MONGO_URI
    db_client = AsyncIOMotorClient(uri)
    db = db_client.get_database("vplay_bot")

async def close_db():
    """Closes the MongoDB client connection."""
    global db_client
    if db_client:
        db_client.close()

# ==========================================
# User connections mappings
# ==========================================

async def set_user_connection(user_id: int, group_id: int, group_title: str):
    """Links a user's DM actions to a specific group chat's voice call."""
    collection = db.get_collection("connections")
    await collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "connected_group_id": group_id,
                "connected_group_title": group_title,
                "updated_at": datetime.datetime.utcnow()
            }
        },
        upsert=True
    )

async def get_user_connection(user_id: int):
    """Retrieves the group connection details for a user."""
    collection = db.get_collection("connections")
    return await collection.find_one({"_id": user_id})

async def clear_user_connection(user_id: int):
    """Removes the connection mapping for a user."""
    collection = db.get_collection("connections")
    await collection.delete_one({"_id": user_id})


# ==========================================
# Playlist management CRUD
# ==========================================

async def create_playlist(user_id: int, name: str) -> str:
    """Creates a new playlist for the user. Returns its string ID."""
    collection = db.get_collection("playlists")
    
    # Check if a playlist with this name already exists for the user
    existing = await collection.find_one({"user_id": user_id, "name": name})
    if existing:
        return str(existing["_id"])
        
    result = await collection.insert_one({
        "user_id": user_id,
        "name": name,
        "videos": [],
        "created_at": datetime.datetime.utcnow()
    })
    return str(result.inserted_id)

async def get_playlists(user_id: int) -> list:
    """Lists all playlists created by the user."""
    collection = db.get_collection("playlists")
    cursor = collection.find({"user_id": user_id}).sort("name", 1)
    return await cursor.to_list(length=100)

async def get_playlist_by_id(playlist_id: str) -> dict:
    """Retrieves a specific playlist by its ID."""
    collection = db.get_collection("playlists")
    try:
        obj_id = ObjectId(playlist_id)
    except Exception:
        return None
    return await collection.find_one({"_id": obj_id})

async def get_playlist_by_name(user_id: int, name: str) -> dict:
    """Retrieves a playlist by its name for a specific user."""
    collection = db.get_collection("playlists")
    return await collection.find_one({"user_id": user_id, "name": name})

async def delete_playlist(playlist_id: str) -> bool:
    """Deletes a playlist from MongoDB."""
    collection = db.get_collection("playlists")
    try:
        obj_id = ObjectId(playlist_id)
    except Exception:
        return False
    result = await collection.delete_one({"_id": obj_id})
    return result.deleted_count > 0

async def add_video_to_playlist(playlist_id: str, file_id: str, file_unique_id: str, name: str, duration: int, file_size: int) -> bool:
    """Appends a video to a specific playlist."""
    collection = db.get_collection("playlists")
    try:
        obj_id = ObjectId(playlist_id)
    except Exception:
        return False
        
    video_item = {
        "file_id": file_id,
        "file_unique_id": file_unique_id,
        "name": name,
        "duration": duration,
        "file_size": file_size,
        "added_at": datetime.datetime.utcnow()
    }
    
    # Avoid duplicate file_unique_id in the same playlist
    playlist = await collection.find_one({"_id": obj_id})
    if playlist:
        for v in playlist.get("videos", []):
            if v["file_unique_id"] == file_unique_id:
                # Update file_id if it changed, but keep names etc.
                await collection.update_one(
                    {"_id": obj_id, "videos.file_unique_id": file_unique_id},
                    {"$set": {"videos.$.file_id": file_id}}
                )
                return True
                
    result = await collection.update_one(
        {"_id": obj_id},
        {"$push": {"videos": video_item}}
    )
    return result.modified_count > 0

async def remove_video_from_playlist(playlist_id: str, file_unique_id: str) -> bool:
    """Removes a video from a specific playlist by its unique ID."""
    collection = db.get_collection("playlists")
    try:
        obj_id = ObjectId(playlist_id)
    except Exception:
        return False
    result = await collection.update_one(
        {"_id": obj_id},
        {"$pull": {"videos": {"file_unique_id": file_unique_id}}}
    )
    return result.modified_count > 0
