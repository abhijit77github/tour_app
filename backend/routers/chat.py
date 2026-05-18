from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from typing import List, Dict
from bson import ObjectId
from datetime import datetime, timedelta, timezone
from ..models.chat import ChatMessage, ChatMessageCreate, ChatConversation
from ..database import get_database
from ..routers.auth import get_current_user
import json

router = APIRouter(prefix="/chat", tags=["Chat"])

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"User {user_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(message)
                return True
            except Exception as e:
                print(f"Error sending message to {user_id}: {e}")
                self.disconnect(user_id)
                return False
        return False


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(user_id, websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Save message to database
            db = await get_database()
            
            now = datetime.now(timezone.utc)
            message_doc = {
                "sender_id": user_id,
                "receiver_id": message_data["receiver_id"],
                "message": message_data["message"],
                "created_at": now,
                "timestamp": now,
                "read": False
            }
            
            result = await db.chat_messages.insert_one(message_doc)
            message_doc["_id"] = str(result.inserted_id)
            
            # Send to receiver if online
            sent = await manager.send_personal_message({
                "type": "new_message",
                "data": {
                    "_id": str(message_doc["_id"]),
                    "sender_id": message_doc["sender_id"],
                    "receiver_id": message_doc["receiver_id"],
                    "message": message_doc["message"],
                    "timestamp": message_doc["timestamp"].isoformat(),
                    "read": False
                }
            }, message_data["receiver_id"])
            
            # Send confirmation back to sender
            await websocket.send_json({
                "type": "message_sent",
                "data": {
                    "_id": str(message_doc["_id"]),
                    "sender_id": message_doc["sender_id"],
                    "receiver_id": message_doc["receiver_id"],
                    "message": message_doc["message"],
                    "timestamp": message_doc["timestamp"].isoformat(),
                    "read": False,
                    "delivered": sent
                }
            })
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)


@router.post("/messages")
async def send_message(
    message: ChatMessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a chat message (HTTP fallback)"""
    db = await get_database()
    
    # Verify receiver exists
    try:
        receiver = await db.users.find_one({"_id": ObjectId(message.receiver_id)})
        if not receiver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiver not found"
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid receiver ID"
        )
    
    # Create message
    now = datetime.now(timezone.utc)
    message_doc = {
        "sender_id": str(current_user["_id"]),
        "receiver_id": message.receiver_id,
        "message": message.message,
        "created_at": now,
        "timestamp": now,
        "read": False
    }
    
    result = await db.chat_messages.insert_one(message_doc)
    message_doc["_id"] = str(result.inserted_id)
    
    # Try to send via WebSocket
    await manager.send_personal_message({
        "type": "new_message",
        "data": {
            "_id": str(message_doc["_id"]),
            "sender_id": message_doc["sender_id"],
            "receiver_id": message_doc["receiver_id"],
            "message": message_doc["message"],
            "timestamp": message_doc["timestamp"].isoformat(),
            "read": False
        }
    }, message.receiver_id)
    
    return {"message": "Message sent", "message_id": str(result.inserted_id)}


@router.get("/messages/{other_user_id}")
async def get_messages(
    other_user_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get chat messages between current user and another user"""
    db = await get_database()
    
    current_user_id = str(current_user["_id"])
    
    # Get messages between the two users
    messages = await db.chat_messages.find({
        "$or": [
            {"sender_id": current_user_id, "receiver_id": other_user_id},
            {"sender_id": other_user_id, "receiver_id": current_user_id}
        ]
    }).sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Convert ObjectId to string
    for msg in messages:
        msg["_id"] = str(msg["_id"])
    
    # Mark received messages as read
    await db.chat_messages.update_many(
        {
            "sender_id": other_user_id,
            "receiver_id": current_user_id,
            "read": False
        },
        {"$set": {"read": True}}
    )
    
    # Reverse to get chronological order
    messages.reverse()
    
    return {"messages": messages}


@router.get("/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    """Get list of all conversations for current user"""
    db = await get_database()
    
    current_user_id = str(current_user["_id"])
    
    # Get all users the current user has chatted with
    pipeline = [
        {
            "$match": {
                "$or": [
                    {"sender_id": current_user_id},
                    {"receiver_id": current_user_id}
                ]
            }
        },
        {
            "$sort": {"timestamp": -1}
        },
        {
            "$group": {
                "_id": {
                    "$cond": [
                        {"$eq": ["$sender_id", current_user_id]},
                        "$receiver_id",
                        "$sender_id"
                    ]
                },
                "last_message": {"$first": "$message"},
                "last_message_time": {"$first": "$timestamp"},
                "messages": {"$push": "$$ROOT"}
            }
        }
    ]
    
    conversations = await db.chat_messages.aggregate(pipeline).to_list(None)
    
    # Get user details and unread counts
    result = []
    for conv in conversations:
        other_user_id = conv["_id"]
        
        # Get other user details
        try:
            other_user = await db.users.find_one({"_id": ObjectId(other_user_id)})
            if not other_user:
                continue
        except:
            continue
        
        # Count unread messages from this user
        unread_count = await db.chat_messages.count_documents({
            "sender_id": other_user_id,
            "receiver_id": current_user_id,
            "read": False
        })
        
        result.append({
            "user_id": current_user_id,
            "other_user_id": other_user_id,
            "other_user_name": other_user.get("full_name", "Unknown"),
            "other_user_type": other_user.get("user_type", "unknown"),
            "last_message": conv["last_message"],
            "last_message_time": conv["last_message_time"].isoformat() if conv["last_message_time"] else None,
            "unread_count": unread_count
        })
    
    # Sort by last message time
    result.sort(key=lambda x: x["last_message_time"] or "", reverse=True)
    
    return {"conversations": result}


@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get total unread message count"""
    db = await get_database()
    
    count = await db.chat_messages.count_documents({
        "receiver_id": str(current_user["_id"]),
        "read": False
    })
    
    return {"unread_count": count}


@router.put("/messages/{message_id}/read")
async def mark_message_read(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a message as read"""
    db = await get_database()
    
    try:
        result = await db.chat_messages.update_one(
            {
                "_id": ObjectId(message_id),
                "receiver_id": str(current_user["_id"])
            },
            {"$set": {"read": True}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        return {"message": "Message marked as read"}
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message ID"
        )


@router.get("/retention-info")
async def get_retention_info():
    """Get information about message retention policy"""
    return {
        "retention_days": 7,
        "retention_seconds": 604800,
        "description": "Messages are automatically deleted after 7 days",
        "policy": "TTL index on created_at field"
    }
