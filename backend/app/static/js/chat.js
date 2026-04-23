/**
 * NORMALAIZER Chat — Alpine.js component
 *
 * Manages rooms, WebSocket connections, and message rendering.
 */

/**
 * Helper: fetch with AbortController timeout.
 * @param {string} url
 * @param {RequestInit} options
 * @param {number} timeoutMs - milliseconds before abort
 * @returns {Promise<Response>}
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    return res;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('__timeout__');
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Classify a caught error into a user-facing message.
 */
function chatUserError(err, fallback) {
  if (err && err.message === '__timeout__') {
    return 'Request timed out. Please try again.';
  }
  return fallback || 'Network error. Check your connection and try again.';
}

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

    // Connection status banner
    connectionStatus: '', // '', 'reconnecting', 'disconnected'
    connectionMessage: '',

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
    // Read receipts: { [otherUserId]: { name, last_read_at: ISO } }
    readReceipts: {},
    // Last message id we've reported as read to the server, to avoid
    // spamming the socket with duplicate reads.
    lastSentReadMessageId: null,
    // Users we've already shown a "joined" system message for in this room
    // session — dedupes reconnects and the server's seed-join loop.
    announcedJoiners: {},

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
    createRoomError: '',

    // Browse public rooms
    showBrowseRooms: false,
    publicRooms: [],
    loadingPublicRooms: false,
    joiningRoomId: null,

    // Room sidebar tab: 'my' or 'browse'
    roomTab: 'my',

    // Invite link
    showInviteModal: false,
    inviteLink: '',
    inviteCopied: false,

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
          this.readReceipts = {};
          this.lastSentReadMessageId = null;
          await this.fetchMessages();
          this.connectWebSocket();
          setTimeout(() => this.markLatestIncomingRead(), 800);
        }
      }

      // When the tab becomes visible again, mark the latest incoming
      // message in the current room as read.
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) this.markLatestIncomingRead();
      });
    },

    // ─── Room List ───

    async fetchRooms() {
      this.loadingRooms = true;
      try {
        const res = await fetchWithTimeout('/rooms', {
          headers: { 'Authorization': 'Bearer ' + this.token },
        }, 10000);
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
        this.showError(chatUserError(e, 'Could not load rooms'));
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
      this.readReceipts = {};
      this.lastSentReadMessageId = null;
      this.announcedJoiners = {};
      this.sidebarOpen = false;

      // Update URL without reload
      history.replaceState(null, '', '/app/room/' + room.id);

      await this.fetchMessages();
      this.connectWebSocket();
      // After WS connects and history loads, mark the latest incoming as read.
      setTimeout(() => this.markLatestIncomingRead(), 800);
    },

    // ─── Messages ───

    async fetchMessages() {
      this.loadingMessages = true;
      try {
        const res = await fetchWithTimeout('/rooms/' + this.currentRoomId + '/messages?limit=100', {
          headers: { 'Authorization': 'Bearer ' + this.token },
        }, 10000);
        if (!res.ok) throw new Error('Failed to load messages');
        const data = await res.json();
        this.messages = data.map(m => this.formatMessage(m));
        this.$nextTick(() => this.scrollToBottom());
      } catch (e) {
        this.showError(chatUserError(e, 'Could not load messages'));
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
        created_at: m.created_at,
        preview_text: null,
        preview_style: null,
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
        this.connectionStatus = '';
        this.connectionMessage = '';
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.handleWsMessage(payload);
        } catch (e) {
          // Ignore malformed messages from server
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
      this.connectionStatus = '';
      this.connectionMessage = '';
      if (this.ws) {
        this.ws.close(1000, 'Room switch');
        this.ws = null;
      }
      this.wsConnected = false;
    },

    scheduleReconnect() {
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        this.connectionStatus = 'disconnected';
        this.connectionMessage = 'Connection lost. Click to reconnect.';
        return;
      }
      this.connectionStatus = 'reconnecting';
      this.connectionMessage = 'Connection lost. Reconnecting...';
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      this.reconnectAttempts++;
      this.reconnectTimer = setTimeout(() => {
        this.connectWebSocket();
      }, delay);
    },

    /**
     * Manual reconnect triggered by user clicking the "Click to reconnect" banner.
     */
    manualReconnect() {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      this.reconnectAttempts = 0;
      this.connectionStatus = 'reconnecting';
      this.connectionMessage = 'Reconnecting...';
      this.connectWebSocket();
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
            created_at: d.created_at,
            preview_text: null,
            preview_style: null,
          });

          this.$nextTick(() => this.scrollToBottom());

          // Remove typing indicator for this sender
          this.typingUsers = this.typingUsers.filter(n => n !== d.sender_name);

          // If this is an incoming message (not our own) and the room is
          // actually being looked at, mark it read immediately.
          if (!isOwn && !document.hidden && this.currentRoomId === this.currentRoomId) {
            this.markRead(d.id);
          }
          break;
        }

        case 'preview': {
          // Sender-only event: how this message reads in the opposite style.
          // Only shown when no one else in a different style is in the room.
          const d = payload.data;
          const msg = this.messages.find(m => m.id === d.message_id);
          if (msg) {
            msg.preview_text = d.preview_text;
            msg.preview_style = d.preview_style;
            this.$nextTick(() => this.scrollToBottom());
          }
          break;
        }

        case 'read_receipt': {
          // A peer has read up to last_read_at. We store it so own messages
          // with created_at <= last_read_at render with a "Read" indicator.
          const d = payload.data;
          if (d.user_id === this.userId) break;  // our own read — ignore
          this.readReceipts[d.user_id] = {
            name: d.display_name || '',
            last_read_at: d.last_read_at,
          };
          break;
        }

        case 'user_joined': {
          const d = payload.data;
          // Dedupe: client reconnects cause multiple join events for the
          // same user. Only show the system message once per room session.
          if (d.user_id && this.announcedJoiners[d.user_id]) break;
          if (d.user_id) this.announcedJoiners[d.user_id] = true;
          // Bump participant count in the sidebar for the current room.
          if (this.currentRoomId) {
            const room = this.rooms.find(r => r.id === this.currentRoomId);
            if (room) room.participant_count = (room.participant_count || 1) + 1;
          }
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
          const errData = payload.data || {};
          const errCode = errData.code || '';
          const errMessage = errData.message || 'An error occurred';

          if (errCode === 'credit_exhausted') {
            // Show upgrade CTA as a persistent system message
            this.messages.push({
              id: 'err-' + Date.now(),
              sender_id: null,
              sender_name: '',
              text: errMessage + ' <a href="/pricing" class="underline font-semibold">Upgrade your plan</a>',
              is_own: false,
              time: this.formatTime(new Date().toISOString()),
              is_system: true,
              is_error: true,
              is_html: true,
            });
            this.showError('Credits exhausted. Please upgrade your plan.');
            this.$nextTick(() => this.scrollToBottom());
          } else if (errCode === 'translation_failed') {
            // Show note that message was sent without translation
            this.messages.push({
              id: 'err-' + Date.now(),
              sender_id: null,
              sender_name: '',
              text: 'Translation unavailable — your message was sent without translation.',
              is_own: false,
              time: this.formatTime(new Date().toISOString()),
              is_system: true,
            });
            this.$nextTick(() => this.scrollToBottom());
          } else {
            this.showError(errMessage);
          }
          break;
        }
      }
    },

    // ─── Send Message ───

    sendMessage() {
      const text = this.messageInput.trim();
      if (!text) return;

      // Check WebSocket is connected and open
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        this.showError('Not connected. Please wait for reconnection or click the banner to reconnect.');
        // Keep the message in the input box — do NOT clear it
        return;
      }

      try {
        this.ws.send(JSON.stringify({
          type: 'send_message',
          text: text,
        }));
        if (typeof track === 'function') track('message_sent', { room_id: this.currentRoomId });
        // Only clear input on successful send
        this.messageInput = '';
      } catch (e) {
        this.showError('Failed to send message. Please try again.');
        // Keep the message in the input box
      }
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
      this.createRoomError = '';
      try {
        const res = await fetchWithTimeout('/rooms', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + this.token,
          },
          body: JSON.stringify({
            name: name,
            is_public: this.newRoomPublic,
          }),
        }, 15000);
        if (!res.ok) {
          const data = await res.json().catch(() => null);
          throw new Error((data && data.detail) || 'Failed to create room');
        }
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
        this.createRoomError = '';
        if (typeof track === 'function') track('room_created', { room_id: mapped.id });
        this.selectRoom(mapped);
      } catch (e) {
        this.createRoomError = chatUserError(e, 'Could not create room. Please try again.');
      } finally {
        this.creatingRoom = false;
      }
    },

    // ─── Browse Public Rooms ───

    async fetchPublicRooms() {
      this.loadingPublicRooms = true;
      try {
        const res = await fetchWithTimeout('/rooms/public', {
          headers: { 'Authorization': 'Bearer ' + this.token },
        }, 10000);
        if (!res.ok) throw new Error('Failed to load public rooms');
        const data = await res.json();
        this.publicRooms = data.map(r => ({
          id: r.id,
          name: r.name,
          is_public: r.is_public,
          owner_id: r.owner_id,
          participant_count: r.participants ? r.participants.length : 0,
        }));
      } catch (e) {
        this.showError(chatUserError(e, 'Could not load public rooms'));
      } finally {
        this.loadingPublicRooms = false;
      }
    },

    async switchTab(tab) {
      this.roomTab = tab;
      if (tab === 'browse') {
        await this.fetchPublicRooms();
      }
    },

    async joinRoom(room) {
      if (this.joiningRoomId) return;
      this.joiningRoomId = room.id;
      try {
        const res = await fetchWithTimeout('/rooms/' + room.id + '/join', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + this.token },
        }, 15000);
        if (!res.ok) throw new Error('Failed to join room');
        const joined = await res.json();
        const mapped = {
          id: joined.id,
          name: joined.name,
          is_public: joined.is_public,
          owner_id: joined.owner_id,
          participant_count: joined.participants ? joined.participants.length : 0,
        };
        // Add to my rooms list if not already there
        if (!this.rooms.find(r => r.id === mapped.id)) {
          this.rooms.unshift(mapped);
        }
        // Remove from public list
        this.publicRooms = this.publicRooms.filter(r => r.id !== room.id);
        // Switch to my rooms tab and select the room
        this.roomTab = 'my';
        this.selectRoom(mapped);
      } catch (e) {
        this.showError(chatUserError(e, 'Could not join room'));
      } finally {
        this.joiningRoomId = null;
      }
    },

    // ─── Invite Link ───

    showRoomInvite() {
      if (!this.currentRoomId) return;
      this.inviteLink = window.location.origin + '/r/' + this.currentRoomId + '/invite';
      this.inviteCopied = false;
      this.showInviteModal = true;
    },

    async copyInviteLink() {
      try {
        await navigator.clipboard.writeText(this.inviteLink);
        this.inviteCopied = true;
        setTimeout(() => { this.inviteCopied = false; }, 2000);
      } catch {
        const input = document.createElement('input');
        input.value = this.inviteLink;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        document.body.removeChild(input);
        this.inviteCopied = true;
        setTimeout(() => { this.inviteCopied = false; }, 2000);
      }
    },

    // ─── Helpers ───

    scrollToBottom() {
      const container = this.$refs.messagesContainer;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    },

    /**
     * Tell the server we've read up to this message id.
     * The server persists last_read_at and broadcasts read_receipt.
     */
    markRead(messageId) {
      if (!messageId) return;
      if (messageId === this.lastSentReadMessageId) return;
      if (!this.wsConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
        // Socket not open yet — retry shortly. selectRoom schedules
        // markLatestIncomingRead 800ms after connectWebSocket, which can
        // still race the handshake on slow links.
        setTimeout(() => this.markRead(messageId), 500);
        return;
      }
      this.lastSentReadMessageId = messageId;
      try {
        this.ws.send(JSON.stringify({ type: 'read', message_id: messageId }));
      } catch (_err) { /* ignore */ }
    },

    /**
     * Find the newest incoming (not-own) message in the current buffer
     * and mark it read. Called on room entry and on tab visibility.
     */
    markLatestIncomingRead() {
      for (let i = this.messages.length - 1; i >= 0; i--) {
        const m = this.messages[i];
        if (m && !m.is_own && !m.is_system && m.id) {
          this.markRead(m.id);
          return;
        }
      }
    },

    /**
     * For an own message, return the name of a peer who has read past it,
     * or null. Used to render "Read by <name>" / "Read".
     */
    readerFor(msg) {
      if (!msg || !msg.is_own || !msg.created_at) return null;
      const createdMs = Date.parse(msg.created_at);
      if (isNaN(createdMs)) return null;
      let reader = null;
      for (const uid of Object.keys(this.readReceipts)) {
        const r = this.readReceipts[uid];
        if (!r || !r.last_read_at) continue;
        if (Date.parse(r.last_read_at) >= createdMs) {
          reader = r.name || 'Read';
          break;
        }
      }
      return reader;
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
        const res = await fetchWithTimeout('/transcripts', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + this.token,
          },
          body: JSON.stringify({ room_id: this.currentRoomId }),
        }, 15000);
        if (!res.ok) throw new Error('Failed to create transcript');
        const data = await res.json();
        this.shareLink = window.location.origin + '/t/' + data.slug;
        this.showShareModal = true;
      } catch (e) {
        this.showError(chatUserError(e, 'Could not create share link'));
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
