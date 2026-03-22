import { useState, useRef, useEffect } from 'react'

const fmt = n => `KES ${Number(n).toLocaleString('en-KE')}`

const WELCOME = {
  text: "Hey! 👋 I'm **Steve**, your Maddest Offers assistant.\n\nI can **find deals for you**, suggest products, compare brands, or answer anything about the offer.\n\nTry: *'Find me an LG fridge'* or *'What's the best air fryer deal?'*",
  isUser: false,
  products: []
}

function parseBold(text) {
  return text.split(/\*\*(.+?)\*\*/g).map((p, i) =>
    i % 2 === 1 ? <strong key={i}>{p}</strong> : p
  )
}

function parseItalic(text) {
  return text.split(/\*(.+?)\*/g).map((p, i) =>
    i % 2 === 1 ? <em key={i}>{p}</em> : parseBold(p)
  )
}

function Bubble({ msg }) {
  const { text, isUser, products } = msg
  const lines = text.split('\n')
  return (
    <div className={`steve-msg ${isUser ? 'user' : 'bot'}`}>
      <div className="bubble">
        {lines.map((line, i) => (
          <span key={i}>
            {isUser ? line : parseItalic(line)}
            {i < lines.length - 1 && <br />}
          </span>
        ))}
      </div>
      {!isUser && products && products.length > 0 && (
        <div className="steve-products">
          {products.map((p, i) => (
            <div className="steve-product-card" key={p.item_code || i}>
              <div className="spc-header">
                <span className="spc-icon">{p.category_icon}</span>
                <span className="spc-brand">{p.brand}</span>
                <span className="spc-disc">{p.new_discount?.toFixed(0)}% OFF</span>
              </div>
              <div className="spc-name">{p.item_name}</div>
              <div className="spc-prices">
                <span className="spc-old">{fmt(p.sale_rrp)}</span>
                <span className="spc-new">{fmt(p.new_promo_rrp)}</span>
              </div>
              <div className="spc-save">Save {fmt(p.sale_rrp - p.new_promo_rrp)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TypingDots() {
  return (
    <div className="steve-msg bot">
      <div className="bubble">
        <div className="typing-dots"><span /><span /><span /></div>
      </div>
    </div>
  )
}

export default function SteveBot() {
  const [open,     setOpen]    = useState(false)
  const [messages, setMessages]= useState([WELCOME])
  const [input,    setInput]   = useState('')
  const [typing,   setTyping]  = useState(false)
  const [badge,    setBadge]   = useState(true)
  const msgsRef  = useRef(null)
  const inputRef = useRef(null)

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
    setMessages(m => [...m, { text: msg, isUser: true, products: [] }])
    setTyping(true)

    try {
      const res  = await fetch('/api/steve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      })
      const data = await res.json()
      setTyping(false)
      setMessages(m => [...m, {
        text: data.response || "I didn't quite catch that. Try again!",
        isUser: false,
        products: data.products || []
      }])
    } catch {
      setTyping(false)
      setMessages(m => [...m, { text: "Oops! Connection lost for a moment. Try again! 🤖", isUser: false, products: [] }])
    }
  }

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  const QUICK = ['Best deal?', 'LG fridge', 'Air fryer deals', 'Under KES 30,000']

  return (
    <div className="steve-wrapper" style={{ pointerEvents: 'none' }}>
      <div className="steve-chat" style={{
        transform: open ? 'scale(1) translateY(0)' : 'scale(0.85) translateY(20px)',
        opacity:   open ? 1 : 0,
        pointerEvents: open ? 'all' : 'none',
      }}>
        <div className="steve-chat-header">
          <div className="steve-avatar-sm">🤖</div>
          <div>
            <strong>Steve</strong>
            <div className="steve-status">● Online — I can find deals for you!</div>
          </div>
          <button className="steve-close" onClick={toggleOpen} aria-label="Close">✕</button>
        </div>

        <div className="steve-messages" ref={msgsRef}>
          {messages.map((m, i) => <Bubble key={i} msg={m} />)}
          {typing && <TypingDots />}
        </div>

        {messages.length <= 2 && (
          <div className="steve-quick-btns">
            {QUICK.map(q => (
              <button key={q} className="steve-quick" onClick={() => {
                setInput(q)
                setTimeout(() => inputRef.current?.focus(), 50)
              }}>{q}</button>
            ))}
          </div>
        )}

        <div className="steve-input-row">
          <input
            ref={inputRef}
            className="steve-input"
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask Steve to find a deal…"
            autoComplete="off"
          />
          <button className="steve-send" onClick={send} aria-label="Send">➤</button>
        </div>
      </div>

      <button className="steve-fab" style={{ pointerEvents: 'auto' }} onClick={toggleOpen} aria-label="Chat with Steve">
        <span className="fab-icon">🤖</span>
        <span className="fab-label">Ask Steve</span>
        {badge && <span className="fab-badge">1</span>}
      </button>
    </div>
  )
}
