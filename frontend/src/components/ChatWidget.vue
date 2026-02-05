<template>
  <div class="chat-widget" :class="{ 'minimized': isMinimized, 'maximized': !isMinimized }">
    <!-- Chat Toggle Button (when minimized) -->
    <button v-if="isMinimized" @click="toggleChat" class="chat-toggle-btn">
      💬 Chat
      <span v-if="chatStore.unreadCount > 0" class="unread-badge">{{ chatStore.unreadCount }}</span>
    </button>

    <!-- Chat Window (when maximized) -->
    <div v-else class="chat-window">
      <!-- Header -->
      <div class="chat-header">
        <div class="chat-title">
          <span v-if="!chatStore.activeConversation">💬 Messages</span>
          <span v-else>{{ chatStore.activeConversation.other_user_name }}</span>
        </div>
        <div class="chat-actions">
          <button @click="toggleChat" class="btn-icon" title="Minimize">−</button>
        </div>
      </div>

      <!-- Conversations List -->
      <div v-if="!chatStore.activeConversation" class="conversations-list">
        <div v-if="chatStore.loading" class="loading-state">Loading...</div>
        
        <div v-else-if="chatStore.conversations.length === 0" class="empty-state">
          <p>No conversations yet</p>
          <p class="hint">Start chatting with operators or tourists!</p>
        </div>
        
        <div v-else class="conversation-items">
          <div 
            v-for="conv in chatStore.conversations" 
            :key="conv.other_user_id"
            @click="selectConversation(conv.other_user_id)"
            class="conversation-item"
          >
            <div class="conversation-avatar">
              {{ conv.other_user_name.charAt(0).toUpperCase() }}
            </div>
            <div class="conversation-info">
              <div class="conversation-name">
                {{ conv.other_user_name }}
                <span class="user-type-badge">{{ conv.other_user_type }}</span>
              </div>
              <div class="conversation-preview">{{ conv.last_message }}</div>
              <div class="conversation-time">{{ formatTime(conv.last_message_time) }}</div>
            </div>
            <div v-if="conv.unread_count > 0" class="unread-indicator">
              {{ conv.unread_count }}
            </div>
          </div>
        </div>
      </div>

      <!-- Messages View -->
      <div v-else class="messages-view">
        <div class="messages-header">
          <button @click="backToConversations" class="btn-back">← Back</button>
        </div>

        <div class="messages-container" ref="messagesContainer">
          <div v-if="chatStore.loading" class="loading-state">Loading messages...</div>
          
          <div v-else-if="chatStore.messages.length === 0" class="empty-messages">
            <p>No messages yet. Start the conversation!</p>
          </div>
          
          <div v-else class="message-list">
            <div 
              v-for="msg in chatStore.messages" 
              :key="msg._id"
              :class="['message', msg.sender_id === currentUserId ? 'sent' : 'received']"
            >
              <div class="message-bubble">
                <p class="message-text">{{ msg.message }}</p>
                <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="message-input-container">
          <input 
            v-model="messageInput"
            @keyup.enter="sendMessage"
            type="text"
            placeholder="Type a message..."
            class="message-input"
          />
          <button @click="sendMessage" :disabled="!messageInput.trim()" class="btn-send">
            Send
          </button>
        </div>
      </div>

      <!-- Connection Status -->
      <div v-if="!chatStore.connected" class="connection-status">
        <span class="status-dot offline"></span>
        <span>Connecting...</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useChatStore } from '../stores/chat';

const authStore = useAuthStore();
const chatStore = useChatStore();

const isMinimized = ref(true);
const messageInput = ref('');
const messagesContainer = ref(null);

const currentUserId = computed(() => authStore.user?.id || authStore.user?._id);
const connectionStatus = computed(() => 
  chatStore.connected ? 'Connected' : chatStore.error ? 'Error' : 'Connecting...'
);

const initializeChatWidget = async () => {
  console.log('=== ChatWidget initializeChatWidget() START ===');
  console.log('authStore.user:', authStore.user);
  console.log('authStore.user?.id:', authStore.user?.id);
  console.log('authStore.user?._id:', authStore.user?._id);
  console.log('currentUserId.value:', currentUserId.value);
  
  if (!currentUserId.value) {
    console.warn('ChatWidget: No user ID available yet');
    console.log('authStore.isAuthenticated:', authStore.isAuthenticated);
    console.log('authStore.token:', authStore.token ? 'EXISTS' : 'NULL');
    return;
  }
  
  try {
    console.log('=== ChatWidget DEBUG ===');
    console.log('Current User ID:', currentUserId.value);
    console.log('Auth User:', authStore.user);
    console.log('import.meta.env.VITE_API_URL:', import.meta.env.VITE_API_URL);
    console.log('window.location.origin:', window.location.origin);
    console.log('Initializing WebSocket for user:', currentUserId.value);
    
    await chatStore.initWebSocket(currentUserId.value);
    
    console.log('WebSocket initialized, loading conversations');
    await chatStore.loadConversations();
    console.log('=== ChatWidget READY ===');
  } catch (error) {
    console.error('ChatWidget: Failed to initialize:', error);
  }
};

onMounted(() => {
  initializeChatWidget();
});

// Watch for user to become available (in case it loads after mount)
watch(() => currentUserId.value, (newId, oldId) => {
  if (newId && !oldId) {
    console.log('ChatWidget: User ID became available, initializing...');
    initializeChatWidget();
  }
});

onUnmounted(() => {
  chatStore.closeWebSocket();
});

// Auto-scroll to bottom when new messages arrive
watch(() => chatStore.messages.length, () => {
  nextTick(() => {
    scrollToBottom();
  });
});

// If a conversation becomes active (e.g., via "Chat with Operator"), auto-open the widget
watch(() => chatStore.activeConversation, (conv) => {
  if (conv) {
    isMinimized.value = false;
    nextTick(() => scrollToBottom());
  }
});

const toggleChat = () => {
  isMinimized.value = !isMinimized.value;
  if (!isMinimized.value && chatStore.conversations.length === 0) {
    chatStore.loadConversations();
  }
};

const selectConversation = async (userId) => {
  await chatStore.setActiveConversation(userId);
  nextTick(() => {
    scrollToBottom();
  });
};

const backToConversations = () => {
  chatStore.clearActiveConversation();
};

const sendMessage = async () => {
  if (!messageInput.value.trim() || !chatStore.activeConversation) return;

  console.log('ChatWidget: Sending message, connected:', chatStore.connected);
  
  const success = await chatStore.sendMessage(
    chatStore.activeConversation.other_user_id,
    messageInput.value
  );

  if (success) {
    messageInput.value = '';
    nextTick(() => {
      scrollToBottom();
    });
  } else {
    console.error('ChatWidget: Failed to send message');
  }
};

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  // Less than a minute
  if (diff < 60000) return 'Just now';
  
  // Less than an hour
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000);
    return `${mins}m ago`;
  }
  
  // Less than a day
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours}h ago`;
  }
  
  // More than a day
  return date.toLocaleDateString();
};
</script>

<style scoped>
.chat-widget {
  position: fixed;
  z-index: 1000;
}

.chat-widget.minimized {
  bottom: 20px;
  right: 20px;
}

.chat-widget.maximized {
  bottom: 0;
  right: 20px;
}

.chat-toggle-btn {
  position: relative;
  padding: 12px 24px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 25px;
  cursor: pointer;
  font-size: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transition: all 0.3s;
}

.chat-toggle-btn:hover {
  background: #45a049;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
}

.unread-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: #f44336;
  color: white;
  border-radius: 50%;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.chat-window {
  width: 380px;
  height: 550px;
  background: white;
  border-radius: 12px 12px 0 0;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  padding: 15px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-title {
  font-weight: 600;
  font-size: 16px;
}

.btn-icon {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s;
}

.btn-icon:hover {
  background: rgba(255, 255, 255, 0.3);
}

.conversations-list {
  flex: 1;
  overflow-y: auto;
}

.conversation-items {
  display: flex;
  flex-direction: column;
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 12px 15px;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  transition: background 0.3s;
}

.conversation-item:hover {
  background: #f5f5f5;
}

.conversation-avatar {
  width: 45px;
  height: 45px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  flex-shrink: 0;
  margin-right: 12px;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-name {
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.user-type-badge {
  font-size: 11px;
  padding: 2px 6px;
  background: #e3f2fd;
  color: #1976d2;
  border-radius: 10px;
  font-weight: normal;
}

.conversation-preview {
  font-size: 13px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.conversation-time {
  font-size: 11px;
  color: #999;
}

.unread-indicator {
  width: 22px;
  height: 22px;
  background: #f44336;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.messages-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.messages-header {
  padding: 10px 15px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.btn-back {
  background: none;
  border: none;
  color: #667eea;
  font-size: 14px;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 5px;
  transition: background 0.3s;
}

.btn-back:hover {
  background: #f0f0f0;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  background: #f9f9f9;
  min-height: 0;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.message {
  display: flex;
}

.message.sent {
  justify-content: flex-end;
}

.message.received {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 18px;
  word-wrap: break-word;
}

.message.sent .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message.received .message-bubble {
  background: white;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.message-text {
  margin: 0 0 4px;
  line-height: 1.4;
}

.message-time {
  font-size: 10px;
  opacity: 0.7;
}

.message-input-container {
  padding: 15px;
  background: white;
  border-top: 1px solid #eee;
  display: flex;
  gap: 10px;
  flex-shrink: 0;
  min-height: 50px;
}

.message-input {
  flex: 1;
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 20px;
  font-size: 14px;
  outline: none;
}

.message-input:focus {
  border-color: #667eea;
}

.btn-send {
  padding: 10px 20px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.3s;
}

.btn-send:hover:not(:disabled) {
  background: #45a049;
}

.btn-send:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.loading-state,
.empty-state,
.empty-messages {
  padding: 40px 20px;
  text-align: center;
  color: #999;
}

.empty-state .hint {
  font-size: 13px;
  margin-top: 8px;
}

.connection-status {
  padding: 8px 15px;
  background: #fff3cd;
  border-top: 1px solid #ffc107;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #856404;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.offline {
  background: #ffc107;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
