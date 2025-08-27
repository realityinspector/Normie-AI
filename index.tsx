/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { GoogleGenAI } from '@google/genai';
import { useState, useRef, useEffect, FormEvent } from 'react';
import ReactDOM from 'react-dom/client';

// --- Data Structures ---
type UserType = 'Neurotypical' | 'Autistic';

interface RoomSettings {
  user1Type: UserType;
  user2Type: UserType;
}

interface Message {
  id: number;
  sender: 'user1' | 'user2';
  originalMessage: string;
  translatedMessage?: string;
  isTranslating: boolean;
}

// --- Gemini AI Setup ---
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

const getSystemInstruction = (senderType: UserType, recipientType: UserType): string => {
  if (senderType === 'Neurotypical' && recipientType === 'Autistic') {
    return `You are a helpful assistant that translates between neurotypical and autistic communication styles. Rephrase the user's message to be more direct, literal, and unambiguous for an autistic person. Only return the translated message.`;
  }
  if (senderType === 'Autistic' && recipientType === 'Neurotypical') {
    return `You are a helpful assistant that translates between autistic and neurotypical communication styles. Rephrase the user's message to add social context, soften blunt statements, and explain literal meanings for a neurotypical person. Only return the translated message.`;
  }
  return 'You are a helpful communication assistant. Rephrase the user\'s message clearly.';
};


// --- Main App Component (Router) ---
function NormieAIApp() {
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    const handleHashChange = () => setHash(window.location.hash);
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const roomId = hash.replace(/^#\/?/, '');

  if (roomId) {
    return <ChatRoom roomId={roomId} />;
  } else {
    return <CreateRoom />;
  }
}


// --- Create Room Component ---
function CreateRoom() {
  const [user1Type, setUser1Type] = useState<UserType>('Neurotypical');
  const [user2Type, setUser2Type] = useState<UserType>('Autistic');

  const handleCreateRoom = () => {
    const roomId = 'room-' + Date.now().toString(36) + Math.random().toString(36).substring(2);
    const settings: RoomSettings = { user1Type, user2Type };
    localStorage.setItem(`normie-ai-room-${roomId}`, JSON.stringify(settings));
    window.location.hash = roomId;
  };

  return (
    <div className="setup-container">
      <header className="chat-header">
        <h1>Normie AI</h1>
        <p>Create a new cultural translation chat room.</p>
      </header>
      <main className="setup-form">
        <div className="participant-settings">
          <label htmlFor="user1Type">Participant 1 Style</label>
          <select id="user1Type" value={user1Type} onChange={(e) => setUser1Type(e.target.value as UserType)}>
            <option>Neurotypical</option>
            <option>Autistic</option>
          </select>
        </div>
        <div className="participant-settings">
          <label htmlFor="user2Type">Participant 2 Style</label>
          <select id="user2Type" value={user2Type} onChange={(e) => setUser2Type(e.target.value as UserType)}>
            <option>Autistic</option>
            <option>Neurotypical</option>
          </select>
        </div>
        <button className="create-room-button" onClick={handleCreateRoom}>Create Chat Room</button>
      </main>
    </div>
  );
}

// --- Chat Room Component ---
function ChatRoom({ roomId }: { roomId: string }) {
  const [settings, setSettings] = useState<RoomSettings | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentUser, setCurrentUser] = useState<'user1' | 'user2' | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [isApiLoading, setIsApiLoading] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const messageListRef = useRef<HTMLDivElement>(null);

  // Load settings and messages from localStorage
  useEffect(() => {
    const roomSettings = localStorage.getItem(`normie-ai-room-${roomId}`);
    const roomMessages = localStorage.getItem(`normie-ai-messages-${roomId}`);
    const sessionUser = sessionStorage.getItem(`normie-ai-user-${roomId}`);
    
    if (roomSettings) setSettings(JSON.parse(roomSettings));
    if (roomMessages) setMessages(JSON.parse(roomMessages));
    if (sessionUser) setCurrentUser(sessionUser as 'user1' | 'user2');
  }, [roomId]);

  // Save messages to localStorage
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(`normie-ai-messages-${roomId}`, JSON.stringify(messages));
    }
  }, [messages, roomId]);

  // Auto-scroll
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSetUser = (user: 'user1' | 'user2') => {
    sessionStorage.setItem(`normie-ai-user-${roomId}`, user);
    setCurrentUser(user);
  };

  const handleSendMessage = async (e: FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isApiLoading || !currentUser || !settings) return;

    const newMessage: Message = {
      id: Date.now(),
      sender: currentUser,
      originalMessage: inputValue,
      isTranslating: true,
    };

    setMessages((prev) => [...prev, newMessage]);
    setInputValue('');
    setIsApiLoading(true);
    
    const senderType = currentUser === 'user1' ? settings.user1Type : settings.user2Type;
    const recipientType = currentUser === 'user1' ? settings.user2Type : settings.user1Type;

    try {
      const response = await ai.models.generateContent({
        model: 'gemini-2.5-flash',
        contents: newMessage.originalMessage,
        config: {
          systemInstruction: getSystemInstruction(senderType, recipientType),
        },
      });
      const translatedText = response.text;
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === newMessage.id
            ? { ...msg, translatedMessage: translatedText, isTranslating: false }
            : msg
        )
      );
    } catch (error) {
      console.error('Error generating content:', error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === newMessage.id
            ? { ...msg, translatedMessage: 'Sorry, translation failed.', isTranslating: false }
            : msg
        )
      );
    } finally {
      setIsApiLoading(false);
    }
  };
  
  const copyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  };

  if (!settings) {
    return <div className="setup-container"><h1>Room not found</h1><p>This chat room does not exist. <a href="/">Create a new one.</a></p></div>;
  }

  if (!currentUser) {
    return (
      <div className="setup-container">
        <h1>Join as...</h1>
        <div className="role-selection">
          <button onClick={() => handleSetUser('user1')}>Participant 1 ({settings.user1Type})</button>
          <button onClick={() => handleSetUser('user2')}>Participant 2 ({settings.user2Type})</button>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-container" aria-live="polite">
      <header className="chat-header">
        <h1>Normie AI Chat</h1>
        <button className="copy-link-button" onClick={copyLink}>{linkCopied ? 'Copied!' : 'Copy Link'}</button>
      </header>
      <main className="message-list" ref={messageListRef}>
        {messages.map((msg) => (
          <div key={msg.id} className={`message-container ${msg.sender === currentUser ? 'sent' : 'received'}`}>
            <div className="message-bubble" role="article" aria-label={`${msg.sender} message`}>
              <div className="original-message">{msg.originalMessage}</div>
              <div className="translated-message">
                {msg.isTranslating ? <i>translating...</i> : msg.translatedMessage}
              </div>
            </div>
             <div className="message-sender-label">{msg.sender === 'user1' ? `P1 (${settings.user1Type})` : `P2 (${settings.user2Type})`}</div>
          </div>
        ))}
      </main>
      <form className="message-form" onSubmit={handleSendMessage}>
        <input
          type="text"
          className="message-input"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Type your message..."
          aria-label="Chat input"
          disabled={isApiLoading}
        />
        <button type="submit" className="send-button" disabled={isApiLoading || !inputValue.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}


const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<NormieAIApp />);