# 7-Day Message Retention - Testing Guide

## ✅ Implementation Complete

### What Was Changed

1. **Backend Startup** - Added TTL index creation in `backend/main.py`:
   - TTL (Time To Live) index on `created_at` field
   - Automatically deletes messages after 7 days (604,800 seconds)
   - Index created on application startup

2. **Chat Router** - Added retention info endpoint in `backend/routers/chat.py`:
   - New endpoint: `GET /chat/retention-info`
   - Returns retention policy details

3. **Documentation** - Updated `CHAT_IMPLEMENTATION.md`:
   - Added 7-day retention to features list
   - Updated database schema with TTL index
   - Added message retention policy explanation

---

## 🧪 How to Test

### Step 1: Restart Backend Server
The TTL index is created on startup. Restart your backend to apply:

```powershell
# Stop current backend if running
# Then start:
cd backend
uvicorn main:app --reload --port 8808
```

**Expected Output on Startup:**
```
✅ Chat message TTL index created (7-day retention)
```

### Step 2: Verify Index Creation
Check MongoDB to confirm the TTL index exists:

```javascript
// In MongoDB shell or Compass
db.chat_messages.getIndexes()

// Should see an index like:
{
  "v": 2,
  "key": { "created_at": 1 },
  "name": "created_at_1",
  "expireAfterSeconds": 604800  // 7 days
}
```

### Step 3: Test Retention Policy API
Call the new endpoint to verify configuration:

```bash
# Using curl (replace with your auth token)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8808/chat/retention-info

# Expected response:
{
  "retention_days": 7,
  "retention_seconds": 604800,
  "description": "Messages are automatically deleted after 7 days",
  "policy": "TTL index on created_at field"
}
```

Or visit in browser (after logging in):
```
http://localhost:8808/chat/retention-info
```

### Step 4: Verify Message Timestamp
Send a test message and check it has `created_at` field:

```bash
# Send a message via API
POST http://localhost:8808/chat/messages
{
  "receiver_id": "some_user_id",
  "message": "Test message"
}

# Check in MongoDB
db.chat_messages.findOne()

# Should have:
{
  "_id": ObjectId(...),
  "sender_id": "...",
  "receiver_id": "...",
  "message": "Test message",
  "created_at": ISODate("2026-01-21T..."),  // Used by TTL
  "timestamp": ISODate("2026-01-21T..."),
  "read": false
}
```

---

## 🔍 How It Works

### MongoDB TTL Index
MongoDB's TTL index automatically deletes documents after a specified time:

1. **Index Creation**: On startup, creates index on `created_at` field
2. **Background Process**: MongoDB runs a background task every 60 seconds
3. **Auto-Deletion**: Deletes documents where `created_at + 604800 seconds < current_time`
4. **Zero Overhead**: No manual cleanup needed, handled by MongoDB

### Message Lifecycle
```
Day 0: Message created → stored with created_at timestamp
Day 1-6: Message visible in chat history
Day 7: MongoDB TTL process deletes message automatically
Day 8+: Message no longer exists in database
```

### Important Notes
- ⏰ TTL background task runs every ~60 seconds (MongoDB default)
- 📅 Deletion happens after 7 full days from `created_at`
- 🔒 Cannot be bypassed - messages will be deleted automatically
- 💾 No data recovery after deletion
- 📊 Reduces database size automatically

---

## 🎯 Benefits

1. **Automatic Cleanup**: No manual intervention needed
2. **Database Efficiency**: Keeps database size manageable
3. **Privacy**: Old conversations automatically removed
4. **Compliance**: Helps meet data retention policies
5. **Performance**: Faster queries with smaller dataset

---

## 🔧 Customization

To change retention period, modify in `backend/main.py`:

```python
# Current: 7 days
expireAfterSeconds=604800

# For 14 days:
expireAfterSeconds=1209600

# For 30 days:
expireAfterSeconds=2592000

# For 1 day (testing):
expireAfterSeconds=86400
```

Then restart the backend to recreate the index.

---

## ⚠️ Important Considerations

1. **First-Time Setup**: If you already have messages in the database without `created_at` field, they won't have TTL applied. Only new messages will be auto-deleted.

2. **Testing TTL**: To test immediately, temporarily set `expireAfterSeconds=60` (1 minute) and send a test message. Wait 1-2 minutes and verify deletion.

3. **Index Recreation**: If you change the TTL value, you must drop the old index first:
   ```javascript
   db.chat_messages.dropIndex("created_at_1")
   ```
   Then restart backend to create new index.

4. **MongoDB Version**: TTL indexes require MongoDB 2.2 or later (you should be fine with Motor 3.3.2).

---

## ✅ Verification Checklist

- [ ] Backend starts without errors
- [ ] Console shows "✅ Chat message TTL index created"
- [ ] `GET /chat/retention-info` returns correct policy
- [ ] New messages have `created_at` field in MongoDB
- [ ] TTL index exists in `db.chat_messages.getIndexes()`
- [ ] (Optional) Test with short TTL to verify auto-deletion

---

## 🎉 Complete!

Your chat system now automatically deletes messages after 7 days. No user action or manual cleanup required!
