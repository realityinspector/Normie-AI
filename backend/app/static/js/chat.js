/**
 * NORMALAIZER Chat — Alpine.js component
 *
 * Manages rooms, WebSocket connections, and message rendering.
 */

function chatApp(token, userId, displayName, initialRoomId) {
  return {
    // Auth
    token,
    userId,
    displayName,

    // UI state
    sidebarOpen: false,
    showCreateRoom: false,
    errorMsg: '',

    // Room list
    rooms: [],
    loadingRooms: true,

    // Current room
    currentRoomId: null,
    currentRoomName: '',

    // Messages
    messages: [],
    loadingMessages: false,
    messageInput: '',

    // WebSocket
    ws: null,
    wsConnected: false,
    reconnectTimer: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 10,

    // Create room
    newRoomName: '',
    newRoomPublic: false,
    creatingRoom: false,

    // Share
    showShareModal: false,
    shareLink: '',
    shareCopied: false,
    creatingTranscript: false,

    // Typing
    typingUsers: [],
    typingTimer: null,

    get typingText() {
      if (this.typingUsers.length === 0) return '';
      if (this.typingUsers.length === 1) return this.typingUsers[0] + ' is typing...';
      return this.typingUsers.join(', ') + ' are typing...';
    },

    // ─── Lifecycle ───

    async init() {
      await this.fetchRooms();

      // Auto-select room if provided via URL
      if (initialRoomId) {
        const room = this.rooms.find(r => r.id === initialRoomId);
        if (room) {
          this.selectRoom(room);
        } else {
          // Room may not be in user's list yet — try to join/load anyway
          this.currentRoomId = initialRoomId;
          this.currentRoomName = 'Loading...';
          await this.fetchMessages();
          this.connectWebSocket();
        }
      }
    },

    // ─── Room List ───

    async fetchRooms() {
      this.loadingRooms = true;
      try {
        const res = await fetch('/rooms', {
          headers: { 'Authorization': 'Bearer ' + this.token },
        });
        if (!res.ok) throw new Error('Failed to load rooms');
        const data = await res.json();
        this.rooms = data.map(r => ({
          id: r.id,
          name: r.name,
          is_public: r.is_public,
          owner_id: r.owner_id,
          participant_count: r.participants ? r.participants.length : 0,
        }));
      } catch (e) {
        this.showError('Could not load rooms');
        console.error(e);
      } finally {
        this.loadingRooms = false;
      }
    },

    async selectRoom(room) {
      if (this.currentRoomId === room.id) {
        this.sidebarOpen = false;
        return;
      }

      // Disconnect previous WebSocket
      this.disconnectWebSocket();

      this.currentRoomId = room.id;
      this.currentRoomName = room.name;
      this.messages = [];
      this.sidebarOpen = false;

      // Update URL without reload
      history.replaceState(null, '', '/app/room/' + room.id);

      await this.fetchMessages();
      this.connectWebSocket();
    },

    // ─── Messages ───

    async fetchMessages() {
      this.loadingMessages = true;
      try {
        const res = await fetch('/rooms/' + this.currentRoomId + '/messages?limit=100', {
          headers: { 'Authorization': 'Bearer ' + this.token },
        });
        if (!res.ok) throw new Error('Failed to load messages');
        const data = await res.json();
        this.messages = data.map(m => this.formatMessage(m));
        this.$nextTick(() => this.scrollToBottom());
      } catch (e) {
        this.showError('Could not load messages');
        console.error(e);
      } finally {
        this.loadingMessages = false;
      }
    },

    formatMessage(m) {
      const isOwn = m.sender_id === this.userId;
      // For own messages show original_text; for others show translated_text or original_text
      const text = isOwn
        ? m.original_text
        : (m.translated_text || m.original_text);

      return {
        id: m.id,
        sender_id: m.sender_id,
        sender_name: m.sender_name || 'Unknown',
        text: text,
        is_own: isOwn,
        time: this.formatTime(m.created_at),
      };
    },

    formatTime(isoStr) {
      try {
        const d = new Date(isoStr);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } catch {
        return '';
      }
    },

    // ─── WebSocket ───

    connectWebSocket() {
      if (!this.currentRoomId || !this.token) return;

      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const url = protocol + '//' + location.host + '/ws/rooms/' + this.currentRoomId + '?token=' + encodeURIComponent(this.token);

      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.wsConnected = true;
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.handleWsMessage(payload);
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };

      this.ws.onclose = (event) => {
        this.wsConnected = false;
        // Don't reconnect if we intentionally closed or room changed
        if (event.code !== 1000 && this.currentRoomId) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = () => {
        this.wsConnected = false;
      };
    },

    disconnectWebSocket() {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      this.reconnectAttempts = 0;
      if (this.ws) {
        this.ws.close(1000, 'Room switch');
        this.ws = null;
      }
      this.wsConnected = false;
    },

    scheduleReconnect() {
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        this.showError('Connection lost. Please refresh the page.');
        return;
      }
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      this.reconnectAttempts++;
      this.reconnectTimer = setTimeout(() => {
        this.connectWebSocket();
      }, delay);
    },

    handleWsMessage(payload) {
      switch (payload.type) {
        case 'message': {
          const d = payload.data;
          const isOwn = d.sender_id === this.userId;
          const text = isOwn
            ? d.original_text
            : (d.translated_text || d.original_text);

          this.messages.push({
            id: d.id,
            sender_id: d.sender_id,
            sender_name: d.sender_name,
            text: text,
            is_own: isOwn,
            time: this.formatTime(d.created_at),
          });

          this.$nextTick(() => this.scrollToBottom());

          // Remove typing indicator for this sender
          this.typingUsers = this.typingUsers.filter(n => n !== d.sender_name);
          break;
        }

        case 'user_joined': {
          const d = payload.data;
          // Optionally show system message
          this.messages.push({
            id: 'sys-' + Date.now(),
            sender_id: null,
            sender_name: '',
            text: (d.display_name || 'Someone') + ' joined the room',
            is_own: false,
            time: this.formatTime(new Date().toISOString()),
            is_system: true,
          });
          this.$nextTick(() => this.scrollToBottom());
          break;
        }

        case 'user_left': {
          // Could show system message
          break;
        }

        case 'typing': {
          const name = payload.data.display_name;
          if (name && !this.typingUsers.includes(name)) {
            this.typingUsers.push(name);
          }
          // Auto-remove after 3s
          setTimeout(() => {
            this.typingUsers = this.typingUsers.filter(n => n !== name);
          }, 3000);
          break;
        }

        case 'error': {
          this.showError(payload.data.message || 'An error occurred');
          break;
        }
      }
    },

    // ─── Send Message ───

    sendMessage() {
      const text = this.messageInput.trim();
      if (!text || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;

      this.ws.send(JSON.stringify({
        type: 'send_message',
        text: text,
      }));

      this.messageInput = '';
    },

    handleTyping() {
      // Optional: send typing indicator
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        if (this.typingTimer) clearTimeout(this.typingTimer);
        this.typingTimer = setTimeout(() => {
          // Typing stopped
        }, 2000);
      }
    },

    // ─── Create Room ───

    async createRoom() {
      const name = this.newRoomName.trim();
      if (!name) return;

      this.creatingRoom = true;
      try {
        const res = await fetch('/rooms', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + this.token,
          },
          body: JSON.stringify({
            name: name,
            is_public: this.newRoomPublic,
          }),
        });
        if (!res.ok) throw new Error('Failed to create room');
        const room = await res.json();
        const mapped = {
          id: room.id,
          name: room.name,
          is_public: room.is_public,
          owner_id: room.owner_id,
          participant_count: room.participants ? room.participants.length : 0,
        };
        this.rooms.unshift(mapped);
        this.showCreateRoom = false;
        this.newRoomName = '';
        this.newRoomPublic = false;
        this.selectRoom(mapped);
      } catch (e) {
        this.showError('Could not create room');
        console.error(e);
      } finally {
        this.creatingRoom = false;
      }
    },

    // ─── Helpers ───

    scrollToBottom() {
      const container = this.$refs.messagesContainer;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    },

    showError(msg) {
      this.errorMsg = msg;
      setTimeout(() => { this.errorMsg = ''; }, 4000);
    },

    // ─── Share Transcript ───

    async shareConversation() {
      if (!this.currentRoomId || this.creatingTranscript) return;

      this.creatingTranscript = true;
      this.shareCopied = false;
      try {
        const res = await fetch('/transcripts', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + this.token,
          },
          body: JSON.stringify({ room_id: this.currentRoomId }),
        });
        if (!res.ok) throw new Error('Failed to create transcript');
        const data = await res.json();
        this.shareLink = window.location.origin + '/t/' + data.slug;
        this.showShareModal = true;
      } catch (e) {
        this.showError('Could not create share link');
        console.error(e);
      } finally {
        this.creatingTranscript = false;
      }
    },

    async copyShareLink() {
      try {
        await navigator.clipboard.writeText(this.shareLink);
        this.shareCopied = true;
        setTimeout(() => { this.shareCopied = false; }, 2000);
      } catch {
        // Fallback for older browsers
        const input = document.createElement('input');
        input.value = this.shareLink;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        document.body.removeChild(input);
        this.shareCopied = true;
        setTimeout(() => { this.shareCopied = false; }, 2000);
      }
    },

    // Alpine $screen helper workaround for sidebar
    $screen(size) {
      const breakpoints = { sm: 640, md: 768, lg: 1024 };
      return window.innerWidth >= (breakpoints[size] || 0);
    },
  };
}
