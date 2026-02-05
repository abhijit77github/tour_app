import { defineStore } from 'pinia';
import api from '../services/api';

export const useChatStore = defineStore('chat', {
  state: () => ({
    userId: null,
    conversations: [],
    activeConversation: null,
    messages: [],
    ws: null,
    connected: false,
    unreadCount: 0,
    loading: false,
    error: null
  }),

  getters: {
    isConnected: (state) => state.connected,
    
    activeMessages: (state) => state.messages,
    
    totalUnread: (state) => state.unreadCount,
    
    getConversationByUserId: (state) => (userId) => {
      return state.conversations.find(c => c.other_user_id === userId);
    }
  },

  actions: {
    async initWebSocket(userId) {
      // Close existing connection if any
      if (this.ws) {
        if (this.connected && this.userId === userId) {
          console.log('WebSocket already connected for this user');
          return Promise.resolve();
        }
        console.log('Closing existing WebSocket connection before creating new one');
        this.closeWebSocket();
      }

      // Build WebSocket URL - ALWAYS use backend port 8808
      // Don't use window.location as it points to frontend (5173)
      const apiBase = import.meta.env.VITE_API_URL;
      let wsUrl;
      
      if (apiBase) {
        // Use configured API URL
        const wsProtocol = apiBase.startsWith('https') ? 'wss' : 'ws';
        const wsHost = apiBase.replace(/^https?:\/\//, '').replace(/\/$/, '');
        wsUrl = `${wsProtocol}://${wsHost}/chat/ws/${userId}`;
      } else {
        // Hardcoded fallback for development
        wsUrl = `ws://localhost:8808/chat/ws/${userId}`;
      }
      
      this.userId = userId;
      
      console.log('VITE_API_URL:', import.meta.env.VITE_API_URL);
      console.log('Connecting to WebSocket:', wsUrl);
      
      return new Promise((resolve, reject) => {
        try {
          this.ws = new WebSocket(wsUrl);

          this.ws.onopen = () => {
            console.log('✅ WebSocket connected successfully');
            this.connected = true;
            this.error = null;
            resolve();
          };

          this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
          };

          this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            this.error = 'WebSocket connection error';
            this.connected = false;
            reject(error);
          };

          this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.connected = false;
            
            // Attempt to reconnect after 3 seconds
            setTimeout(() => {
              if (!this.connected) {
                console.log('Attempting to reconnect...');
                this.initWebSocket(userId).catch(console.error);
              }
            }, 3000);
          };

          // Timeout after 5 seconds
          setTimeout(() => {
            if (!this.connected) {
              console.warn('⚠️ WebSocket connection timeout');
              reject(new Error('Connection timeout'));
            }
          }, 5000);

        } catch (error) {
          console.error('Failed to initialize WebSocket:', error);
          this.error = 'Failed to connect to chat server';
          reject(error);
        }
      });
    },

    async ensureConnected(userId) {
      const uid = userId || this.userId;
      if (!uid) {
        console.warn('No user ID available for WebSocket connection');
        return false;
      }
      if (!this.connected) {
        try {
          await this.initWebSocket(uid);
          console.log('WebSocket connection ensured');
          return true;
        } catch (error) {
          console.error('Failed to ensure WebSocket connection:', error);
          return false;
        }
      }
      return true;
    },

    handleWebSocketMessage(data) {
      if (data.type === 'new_message') {
        const message = data.data;
        
        // Add to messages if it's for the active conversation
        if (this.activeConversation && 
            (message.sender_id === this.activeConversation.other_user_id ||
             message.receiver_id === this.activeConversation.other_user_id)) {
          this.messages.push(message);
          // Active thread, mark read by refreshing unread count
          this.loadUnreadCount();
        } else {
          // New message for another conversation - bump unread
          this.unreadCount += 1;
        }
        
        // Update conversations list
        this.loadConversations();
      } else if (data.type === 'message_sent') {
        // Message sent confirmation
        const message = data.data;
        
        // Update the message in the list (add delivered status)
        const index = this.messages.findIndex(m => 
          m.message === message.message && 
          m.timestamp === message.timestamp
        );
        
        if (index !== -1) {
          this.messages[index] = message;
        } else {
          this.messages.push(message);
        }
      }
    },

    async sendMessage(receiverId, message) {
      if (!message.trim()) return;

      const connected = await this.ensureConnected();

      const messageData = {
        receiver_id: receiverId,
        message: message.trim()
      };

      // Try WebSocket first
      if (connected && this.connected && this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          console.log('📤 Sending message via WebSocket');
          this.ws.send(JSON.stringify(messageData));
          return true;
        } catch (error) {
          console.error('WebSocket send failed:', error);
          // Fall back to HTTP
        }
      } else {
        console.log('⚠️ WebSocket not ready, using HTTP fallback. Connected:', this.connected, 'ReadyState:', this.ws?.readyState);
      }

      // HTTP fallback
      try {
        console.log('📤 Sending message via HTTP');
        await api.post('/chat/messages', messageData);
        return true;
      } catch (error) {
        console.error('Failed to send message:', error);
        this.error = 'Failed to send message';
        return false;
      }
    },

    async loadConversations() {
      this.loading = true;
      try {
        const response = await api.get('/chat/conversations');
        this.conversations = response.data.conversations;
        
        // Update total unread count
        this.unreadCount = this.conversations.reduce((sum, conv) => sum + conv.unread_count, 0);
      } catch (error) {
        console.error('Failed to load conversations:', error);
        this.error = 'Failed to load conversations';
      } finally {
        this.loading = false;
      }
    },

    async loadMessages(otherUserId) {
      this.loading = true;
      try {
        const response = await api.get(`/chat/messages/${otherUserId}`);
        this.messages = response.data.messages;
        
        // Find and set active conversation
        const conversation = this.conversations.find(c => c.other_user_id === otherUserId);
        if (conversation) {
          this.activeConversation = conversation;
          conversation.unread_count = 0; // Mark as read
        }
        
        // Update unread count
        await this.loadUnreadCount();
      } catch (error) {
        console.error('Failed to load messages:', error);
        this.error = 'Failed to load messages';
      } finally {
        this.loading = false;
      }
    },

    async loadUnreadCount() {
      try {
        const response = await api.get('/chat/unread-count');
        this.unreadCount = response.data.unread_count;
      } catch (error) {
        console.error('Failed to load unread count:', error);
      }
    },

    async setActiveConversation(userId) {
      const conversation = this.conversations.find(c => c.other_user_id === userId);
      if (conversation) {
        this.activeConversation = conversation;
        await this.loadMessages(userId);
      }
    },

    async openConversation(otherUserId, otherUserName, otherUserType) {
      await this.ensureConnected();

      // If conversation already exists, load it
      const existing = this.conversations.find(c => c.other_user_id === otherUserId);
      if (existing) {
        this.activeConversation = existing;
        await this.loadMessages(otherUserId);
        return;
      }

      // Otherwise start a fresh conversation shell
      this.activeConversation = {
        user_id: this.userId,
        other_user_id: otherUserId,
        other_user_name: otherUserName,
        other_user_type: otherUserType,
        unread_count: 0,
        messages: []
      };
      this.messages = [];
    },

    closeWebSocket() {
      if (this.ws) {
        console.log('Closing WebSocket connection');
        // Remove event listeners to prevent reconnection attempts
        this.ws.onclose = null;
        this.ws.onerror = null;
        this.ws.onmessage = null;
        this.ws.onopen = null;
        
        if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
          this.ws.close();
        }
        this.ws = null;
        this.connected = false;
        this.userId = null;
      }
    },

    clearActiveConversation() {
      this.activeConversation = null;
      this.messages = [];
    }
  }
});
