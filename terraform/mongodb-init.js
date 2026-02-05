db.auth('admin', 'admin');

const db = db.getSiblingDB('tour_app');

// Create collections with schema validation
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['email', 'password', 'user_type'],
      properties: {
        _id: { bsonType: 'objectId' },
        email: { bsonType: 'string' },
        password: { bsonType: 'string' },
        full_name: { bsonType: 'string' },
        user_type: { enum: ['operator', 'tourist'] },
        created_at: { bsonType: 'date' },
        updated_at: { bsonType: 'date' }
      }
    }
  }
});

db.createCollection('operator_profiles');
db.createCollection('bookings');
db.createCollection('ratings');
db.createCollection('chat_messages');
db.createCollection('quotes');

// Create indexes
db.users.createIndex({ email: 1 }, { unique: true });
db.operator_profiles.createIndex({ user_id: 1 }, { unique: true });
db.bookings.createIndex({ tourist_id: 1 });
db.bookings.createIndex({ operator_id: 1 });
db.ratings.createIndex({ operator_id: 1 });
db.ratings.createIndex({ booking_id: 1 }, { unique: true });
db.chat_messages.createIndex({ sender_id: 1 });
db.chat_messages.createIndex({ receiver_id: 1 });
db.chat_messages.createIndex({ created_at: 1 }, { expireAfterSeconds: 604800 });
db.quotes.createIndex({ tourist_id: 1 });
db.quotes.createIndex({ created_at: 1 });

print('Database initialized successfully!');
