/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { GoogleGenAI } from '@google/genai';
import { useState, useRef, useEffect, FormEvent, MouseEvent, ChangeEvent } from 'react';
import ReactDOM from 'react-dom/client';
// FIX: The error "Module '"firebase/app"' has no exported member 'initializeApp'" indicates
// a Firebase version mismatch. The code uses v9 syntax, but the environment seems to have
// v8. This has been refactored to use the Firebase v8 (namespaced) API.
// FIX: Corrected Firebase imports to use the v9 compatibility layer for v8 syntax support. This resolves all subsequent Firebase-related type errors.
import firebase from 'firebase/compat/app';
import 'firebase/compat/auth';
import 'firebase/compat/firestore';


// --- Firebase Setup ---
const firebaseConfig = {
  apiKey: "AIzaSyAYedbZIfKmnIBUswJHIJxd9vCeMUWjrBk",
  authDomain: "normie-ai-66ef2.firebaseapp.com",
  projectId: "normie-ai-66ef2",
  storageBucket: "normie-ai-66ef2.appspot.com",
  messagingSenderId: "216729382254",
  appId: "1:216729382254:web:2e534e0b3c630b4828257f",
  measurementId: "G-ZZ4PVFKKPD"
};

// FIX: Use Firebase v8 initialization.
if (!firebase.apps.length) {
  firebase.initializeApp(firebaseConfig);
}
const auth = firebase.auth();
const db = firebase.firestore();

// --- Data Structures ---
type UserType = 'Neurotypical' | 'Autistic';

interface AppUser {
  uid: string;
  displayName: string | null;
  email: string | null;
  photoURL: string | null;
  communicationStyle: UserType;
}

interface Room {
  id: string;
  name: string;
  isPublic: boolean;
  ownerId: string;
  participants: string[];
  participantDetails?: { [uid: string]: Pick<AppUser, 'displayName' | 'photoURL' | 'communicationStyle'> };
}

interface Message {
  id: string;
  senderId: string;
  originalMessage: string;
  // Store translations in a map where key is recipient UID
  translations: { [key: string]: string };
  createdAt: any;
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

// --- Authentication ---
const useAuth = () => {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // FIX: Use Firebase v8 onAuthStateChanged and firebase.User type.
    const unsubscribe = auth.onAuthStateChanged(async (firebaseUser: firebase.User | null) => {
      if (firebaseUser) {
        // FIX: Use Firebase v8 Firestore syntax.
        const userRef = db.collection('users').doc(firebaseUser.uid);
        const userSnap = await userRef.get();
        if (userSnap.exists) {
          setUser(userSnap.data() as AppUser);
        } else {
          // Create new user profile
          const newUser: AppUser = {
            uid: firebaseUser.uid,
            displayName: firebaseUser.displayName,
            email: firebaseUser.email,
            photoURL: firebaseUser.photoURL,
            communicationStyle: 'Neurotypical', // Default style
          };
          // FIX: Use Firebase v8 Firestore syntax.
          await userRef.set(newUser);
          setUser(newUser);
        }
      } else {
        setUser(null);
      }
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  return { user, loading };
};

// --- Main App Component (Router) ---
function NormieAIApp() {
  const { user, loading } = useAuth();
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    const handleHashChange = () => setHash(window.location.hash);
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const roomId = hash.startsWith('#/room/') ? hash.replace('#/room/', '') : null;

  if (loading) {
    return <div className="setup-container"><h1>Loading...</h1></div>;
  }

  if (roomId) {
    return <ChatRoom roomId={roomId} currentUser={user} />;
  }

  if (user) {
    return <Dashboard user={user} />;
  }

  return <LoginScreen />;
}

// --- Login Screen ---
function LoginScreen() {
  const handleLogin = async () => {
    // FIX: Use Firebase v8 auth provider.
    const provider = new firebase.auth.GoogleAuthProvider();
    try {
      // FIX: Use Firebase v8 signInWithPopup method.
      await auth.signInWithPopup(provider);
      window.location.hash = ''; // Go to dashboard after login
    } catch (error) {
      console.error("Authentication failed:", error);
    }
  };
  return (
    <div className="setup-container">
      <h1>Welcome to Normie AI</h1>
      <p>A cultural translation messenger application.</p>
      <button className="create-room-button" onClick={handleLogin}>Sign in with Google</button>
    </div>
  );
}

// --- Dashboard ---
function Dashboard({ user }: { user: AppUser }) {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateModalOpen, setCreateModalOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<Room | null>(null);
  const [communicationStyle, setCommunicationStyle] = useState<UserType>(user.communicationStyle);

  useEffect(() => {
    // FIX: Use Firebase v8 Firestore query and snapshot syntax.
    const q = db.collection('rooms').where('participants', 'array-contains', user.uid);
    const unsubscribe = q.onSnapshot((querySnapshot) => {
      const userRooms: Room[] = [];
      querySnapshot.forEach((doc) => {
        userRooms.push({ id: doc.id, ...doc.data() } as Room);
      });
      setRooms(userRooms);
      setLoading(false);
    });
    return () => unsubscribe();
  }, [user.uid]);
  
    const handleStyleChange = async (e: ChangeEvent<HTMLSelectElement>) => {
        const newStyle = e.target.value as UserType;
        setCommunicationStyle(newStyle);
        await db.collection('users').doc(user.uid).update({ communicationStyle: newStyle });
    };

  const createNewRoom = async (name: string, isPublic: boolean) => {
    // FIX: Use Firebase v8 Firestore add and serverTimestamp syntax.
    const newRoomRef = await db.collection('rooms').add({
      name,
      isPublic,
      ownerId: user.uid,
      participants: [user.uid],
      createdAt: firebase.firestore.FieldValue.serverTimestamp(),
    });
    window.location.hash = `#/room/${newRoomRef.id}`;
  };
  
  const updateRoom = async (roomId: string, name: string, isPublic: boolean) => {
      await db.collection('rooms').doc(roomId).update({ name, isPublic });
      setEditingRoom(null);
  };

  const deleteRoom = async (roomId: string) => {
      if(window.confirm('Are you sure you want to delete this room? This cannot be undone.')) {
        await db.collection('rooms').doc(roomId).delete();
      }
  };

  const handleSignOut = async () => {
    // FIX: Use Firebase v8 signOut method.
    await auth.signOut();
    window.location.hash = '';
  }

  return (
    <div className="dashboard-container">
       <header className="chat-header">
        <h1>Dashboard</h1>
        <div>
          <span className="user-display-name">Welcome, {user.displayName}</span>
          <button className="sign-out-button" onClick={handleSignOut}>Sign Out</button>
        </div>
      </header>
       <div className="dashboard-content">
            <aside className="settings-panel">
                <h2>My Settings</h2>
                <div className="form-group">
                    <label htmlFor="commStyle">Your Communication Style</label>
                    <select id="commStyle" value={communicationStyle} onChange={handleStyleChange}>
                        <option value="Neurotypical">Neurotypical</option>
                        <option value="Autistic">Autistic</option>
                    </select>
                </div>
            </aside>
            <main className="room-list">
                 <h2>Your Conversations</h2>
                {loading && <p>Loading rooms...</p>}
                {!loading && rooms.length === 0 && <p>You have no chat rooms yet. Create one to get started!</p>}
                {rooms.map(room => (
                  <div key={room.id} className="room-item">
                    <div className="room-info">
                        <h3>{room.name}</h3>
                        <p>{room.isPublic ? 'Public' : 'Private'}</p>
                    </div>
                    <div className="room-actions">
                      <a className="button" href={`#/room/${room.id}`}>Enter</a>
                      {user.uid === room.ownerId && (
                        <>
                            <button className="button-secondary" onClick={() => setEditingRoom(room)}>Edit</button>
                            <button className="button-danger" onClick={() => deleteRoom(room.id)}>Delete</button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
            </main>
       </div>
      <div className="dashboard-actions">
         <button className="create-room-button" onClick={() => setCreateModalOpen(true)}>Create New Room</button>
      </div>
      {isCreateModalOpen && <CreateRoomModal onClose={() => setCreateModalOpen(false)} onCreate={createNewRoom}/>}
      {editingRoom && <EditRoomModal room={editingRoom} onClose={() => setEditingRoom(null)} onUpdate={updateRoom} />}
    </div>
  );
}

// --- Create & Edit Room Modals ---
function CreateRoomModal({ onClose, onCreate }: { onClose: () => void, onCreate: (name: string, isPublic: boolean) => void }) {
    const [name, setName] = useState('');
    const [isPublic, setIsPublic] = useState(false);

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        if(name.trim()) {
            onCreate(name, isPublic);
        }
    }

    return (
        <div className="modal-backdrop">
            <div className="modal-content">
                <h2>Create New Chat Room</h2>
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="roomName">Room Name</label>
                        <input id="roomName" type="text" value={name} onChange={e => setName(e.target.value)} required />
                    </div>
                    <div className="form-group-checkbox">
                        <input id="isPublic" type="checkbox" checked={isPublic} onChange={e => setIsPublic(e.target.checked)} />
                        <label htmlFor="isPublic">Make room public?</label>
                    </div>
                    <div className="modal-actions">
                        <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
                        <button type="submit" className="button">Create</button>
                    </div>
                </form>
            </div>
        </div>
    )
}

function EditRoomModal({ room, onClose, onUpdate }: { room: Room, onClose: () => void, onUpdate: (roomId: string, name: string, isPublic: boolean) => void }) {
    const [name, setName] = useState(room.name);
    const [isPublic, setIsPublic] = useState(room.isPublic);

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        if(name.trim()) {
            onUpdate(room.id, name, isPublic);
        }
    }

    return (
        <div className="modal-backdrop">
            <div className="modal-content">
                <h2>Edit Room</h2>
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="roomName">Room Name</label>
                        <input id="roomName" type="text" value={name} onChange={e => setName(e.target.value)} required />
                    </div>
                    <div className="form-group-checkbox">
                        <input id="isPublic" type="checkbox" checked={isPublic} onChange={e => setIsPublic(e.target.checked)} />
                        <label htmlFor="isPublic">Make room public?</label>
                    </div>
                    <div className="modal-actions">
                        <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
                        <button type="submit" className="button">Save Changes</button>
                    </div>
                </form>
            </div>
        </div>
    )
}


// --- Chat Room Component ---
function ChatRoom({ roomId, currentUser }: { roomId: string, currentUser: AppUser | null }) {
  const [room, setRoom] = useState<Room | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isApiLoading, setIsApiLoading] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageListRef = useRef<HTMLDivElement>(null);
  
  // Create a stable guest ID for the session
  const [guestId] = useState(() => {
    let id = sessionStorage.getItem('guest-id');
    if (!id) {
        id = `guest_${Math.random().toString(36).substring(2, 11)}`;
        sessionStorage.setItem('guest-id', id);
    }
    return id;
  });

  useEffect(() => {
    // FIX: Use Firebase v8 Firestore syntax.
    const roomRef = db.collection('rooms').doc(roomId);
    const unsubscribeRoom = roomRef.onSnapshot(async (docSnap) => {
      if (docSnap.exists) {
        const roomData = { id: docSnap.id, ...docSnap.data() } as Room;
        
        // Fetch participant details
        const participantDetails: Room['participantDetails'] = {};
        for(const uid of roomData.participants) {
            // FIX: Use Firebase v8 Firestore syntax.
            const userSnap = await db.collection('users').doc(uid).get();
            if(userSnap.exists){
                const userData = userSnap.data() as AppUser;
                participantDetails[uid] = {
                    displayName: userData.displayName,
                    photoURL: userData.photoURL,
                    communicationStyle: userData.communicationStyle
                };
            }
        }
        roomData.participantDetails = participantDetails;
        

        // Check permissions
        if (!roomData.isPublic && (!currentUser || !roomData.participants.includes(currentUser.uid))) {
             setError('This room is private. You do not have access.');
        } else {
             setError(null);
        }
        setRoom(roomData); // Set room after permission check

      } else {
        setError('Room not found. This chat room does not exist.');
      }
    }, (err) => {
        console.error("Error fetching room:", err);
        setError("Could not load the chat room. Please check the link or your connection.");
    });

    // FIX: Use Firebase v8 Firestore query and snapshot syntax.
    const messagesQuery = db.collection('rooms').doc(roomId).collection('messages').orderBy('createdAt', 'asc');
    const unsubscribeMessages = messagesQuery.onSnapshot((querySnapshot) => {
      const msgs: Message[] = [];
      querySnapshot.forEach(doc => {
        msgs.push({ id: doc.id, ...doc.data() } as Message);
      });
      setMessages(msgs);
    });

    return () => {
      unsubscribeRoom();
      unsubscribeMessages();
    };
  }, [roomId, currentUser]);

  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);

  const getGuestMessageCount = () => Number(sessionStorage.getItem(`guest-msg-count-${roomId}`) || '0');
  const incrementGuestMessageCount = () => sessionStorage.setItem(`guest-msg-count-${roomId}`, (getGuestMessageCount() + 1).toString());


  const handleSendMessage = async (e: FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isApiLoading || !room) return;

    const isGuest = !currentUser;

    if (isGuest) {
        if (!room.isPublic) {
            alert("This is a private room. Please sign in to participate.");
            return;
        }
        if (getGuestMessageCount() >= 5) {
            alert("You have reached the message limit for guests. Please sign in to continue chatting.");
            return;
        }
    }
    
    // Auto-join room on first message for logged-in users
    if (currentUser && !room.participants.includes(currentUser.uid)) {
        await db.collection('rooms').doc(roomId).update({
            participants: firebase.firestore.FieldValue.arrayUnion(currentUser.uid)
        });
    }

    setIsApiLoading(true);
    const originalMessage = inputValue;
    setInputValue('');

    try {
        if (isGuest) {
            await db.collection('rooms').doc(roomId).collection('messages').add({
                senderId: guestId,
                originalMessage: originalMessage,
                translations: {},
                createdAt: firebase.firestore.FieldValue.serverTimestamp(),
            });
            incrementGuestMessageCount();
        } else {
            const translations: { [key: string]: string } = {};
            const recipients = room.participantDetails ? Object.entries(room.participantDetails).filter(([uid]) => uid !== currentUser.uid) : [];
            for (const [recipientId, recipientDetails] of recipients) {
                if (currentUser.communicationStyle !== recipientDetails.communicationStyle) {
                    const response = await ai.models.generateContent({
                        model: 'gemini-2.5-flash',
                        contents: originalMessage,
                        config: {
                            systemInstruction: getSystemInstruction(currentUser.communicationStyle, recipientDetails.communicationStyle),
                        },
                    });
                    translations[recipientId] = response.text;
                } else {
                    translations[recipientId] = originalMessage; // No translation needed
                }
            }

            await db.collection('rooms').doc(roomId).collection('messages').add({
                senderId: currentUser.uid,
                originalMessage: originalMessage,
                translations: translations,
                createdAt: firebase.firestore.FieldValue.serverTimestamp(),
            });
        }
    } catch (err) {
      console.error('Error generating content or sending message:', err);
      setInputValue(originalMessage);
    } finally {
      setIsApiLoading(false);
    }
  };

  const copyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  };

  const handleGoToDashboard = (e: MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    window.location.hash = '';
  };
  
  const canSendMessage = () => {
    if (!currentUser) {
        return room?.isPublic && getGuestMessageCount() < 5;
    }
    return true;
  }
  
  const getPlaceholderText = () => {
      if (!room) return "Loading...";
      if (!currentUser && !room.isPublic) return "Please sign in to join this private chat.";
      if (!currentUser && getGuestMessageCount() >= 5) return "Sign in to send more messages.";
      if (canSendMessage()) return "Type your message...";
      return "Cannot send message at this time.";
  }

  if (error) {
    return <div className="setup-container"><h1>Error</h1><p>{error} <a href="#" onClick={handleGoToDashboard}>Go to Dashboard.</a></p></div>;
  }
  
  if (!room) {
    return <div className="setup-container"><h1>Loading Chat...</h1></div>;
  }
  
  const getSenderName = (senderId: string) => {
    if (senderId.startsWith('guest_')) return 'Guest';
    return room?.participantDetails?.[senderId]?.displayName || 'User';
  }
  
  const effectiveSenderId = currentUser ? currentUser.uid : guestId;

  return (
    <div className="chat-container" aria-live="polite">
      <header className="chat-header">
        <h1>{room.name}</h1>
        <button className="copy-link-button" onClick={copyLink}>{linkCopied ? 'Copied!' : 'Copy Invite Link'}</button>
      </header>
      <main className="message-list" ref={messageListRef}>
        {messages.map((msg) => {
            const isSender = effectiveSenderId === msg.senderId;
            const receivedTranslation = msg.translations[currentUser?.uid || ''];

            return (
                 <div key={msg.id} className={`message-container ${isSender ? 'sent' : 'received'}`}>
                    <div className="message-bubble" role="article">
                        {isSender ? (
                            <>
                                <div className="original-message">{msg.originalMessage}</div>
                                {Object.entries(msg.translations).length > 0 && (
                                    <div className="translations-display">
                                        {Object.entries(msg.translations).map(([recipientId, text]) => (
                                            <div key={recipientId} className="translation-item">
                                                For {getSenderName(recipientId)}: "{text}"
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </>
                        ) : (
                             <div className="translated-message only-translation">
                                {receivedTranslation || msg.originalMessage}
                             </div>
                        )}
                    </div>
                    <div className="message-sender-label">{getSenderName(msg.senderId)}</div>
                </div>
            )
        })}
      </main>
      <form className="message-form" onSubmit={handleSendMessage}>
        <input
          type="text"
          className="message-input"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={getPlaceholderText()}
          aria-label="Chat input"
          disabled={isApiLoading || !canSendMessage()}
        />
        <button type="submit" className="send-button" disabled={isApiLoading || !inputValue.trim() || !canSendMessage()}>
          Send
        </button>
      </form>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<NormieAIApp />);