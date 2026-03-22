import { useState, useRef, useEffect } from 'react'

const WELCOME = "Hey! 👋 I'm **Steve**, your Maddest Offers assistant at Axon Lattice. Ask me anything about deals, brands, categories, or how to search!"

function parseBold(text) {
  // Convert **bold** to <strong>
  const parts = text.split(/\*\*(.+?)\*\*/g)
  return parts.map((p, i) =>
    i % 2 === 1 ? <strong key={i}>{p}</strong> : p
  )
}

function Bubble({ text, isUser }) {
  const lines = text.split('\n')
  return (
    <div className={`steve-msg ${isUser ? 'user' : 'bot'}`}>
      <div className="bubble">
        {lines.map((line, i) => (
          <span key={i}>
            {isUser ? line : parseBold(line)}
            {i < lines.length - 1 && <br />}
          </span>
        ))}
      </div>
    </div>
  )
}

function TypingDots() {
  return (
    <div className="steve-msg bot">
      <div className="bubble">
        <div className="typing-dots">
          <span /><span /><span />
        </div>
      </div>
    </div>
  )
}

export default function SteveBot() {
  const [open,     setOpen]    = useState(false)
  const [messages, setMessages]= useState([{ text: WELCOME, isUser: false }])
  const [input,    setInput]   = useState('')
  const [typing,   setTyping]  = useState(false)
  const [badge,    setBadge]   = useState(true)
  const msgsRef = useRef(null)
  const inputRef= useRef(null)

  // scroll to bottom whenever messages change
  useEffect(() => {
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight
  }, [messages, typing])

  const toggleOpen = () => {
    setOpen(o => !o)
    setBadge(false)
    setTimeout(() => inputRef.current?.focus(), 300)
  }

  const send = async () => {
    const msg = input.trim()
    if (!msg) return
    setInput('')
    setMessages(m => [...m, { text: msg, isUser: true }])
    setTyping(true)

    try {
      const res  = await fetch('/api/steve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      })
      const data = await res.json()
      setTyping(false)
      setMessages(m => [...m, { text: data.response, isUser: false }])
    } catch {
      setTyping(false)
      setMessages(m => [...m, { text: "Oops! Lost connection for a moment. Try again! 🤖", isUser: false }])
    }
  }

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div className="steve-wrapper">
      {/* Chat window */}
      <div
        className="steve-chat"
        style={{
          transform: open ? 'scale(1) translateY(0)' : 'scale(0.85) translateY(20px)',
          opacity:   open ? 1 : 0,
          pointerEvents: open ? 'all' : 'none',
        }}
      >
        <div className="steve-chat-header">
          <div className="steve-avatar-sm">🤖</div>
          <div>
            <strong>Steve</strong>
            <div className="steve-status">● Online — Ask me anything!</div>
          </div>
          <button className="steve-close" onClick={toggleOpen} aria-label="Close">✕</button>
        </div>

        <div className="steve-messages" ref={msgsRef}>
          {messages.map((m, i) => <Bubble key={i} text={m.text} isUser={m.isUser} />)}
          {typing && <TypingDots />}
        </div>

        <div className="steve-input-row">
          <input
            ref={inputRef}
            className="steve-input"
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask Steve anything…"
            autoComplete="off"
          />
          <button className="steve-send" onClick={send} aria-label="Send">➤</button>
        </div>
      </div>

      {/* FAB */}
      <button className="steve-fab" onClick={toggleOpen} aria-label="Chat with Steve">
        <span className="fab-icon">🤖</span>
        <span className="fab-label">Ask Steve</span>
        {badge && <span className="fab-badge">1</span>}
      </button>
    </div>
  )
}
