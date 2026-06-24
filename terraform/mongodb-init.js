const appDb = db.getSiblingDB('tour_app_db');

[
  'users',
  'operator_profiles',
  'bookings',
  'ratings',
  'chat_messages',
  'quotes',
  'organizations',
  'organization_memberships',
  'access_roles',
  'notification_templates',
  'notification_campaigns',
  'notification_deliveries'
].forEach((name) => {
  if (!appDb.getCollectionNames().includes(name)) {
    appDb.createCollection(name);
  }
});

appDb.users.createIndex({ email: 1 }, { unique: true });
appDb.operator_profiles.createIndex({ user_id: 1 }, { unique: true });
appDb.bookings.createIndex({ tourist_id: 1 });
appDb.bookings.createIndex({ operator_id: 1 });
appDb.ratings.createIndex({ operator_id: 1 });
appDb.ratings.createIndex({ booking_id: 1 }, { unique: true });
appDb.chat_messages.createIndex({ sender_id: 1 });
appDb.chat_messages.createIndex({ receiver_id: 1 });
appDb.chat_messages.createIndex({ created_at: 1 }, { expireAfterSeconds: 604800 });
appDb.quotes.createIndex({ tourist_id: 1 });
appDb.quotes.createIndex({ created_at: 1 });

print('Database initialized successfully for tour_app_db');
