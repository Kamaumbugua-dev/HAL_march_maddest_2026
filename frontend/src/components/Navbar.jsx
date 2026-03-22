import { useState } from 'react'

export default function Navbar({ page, setPage }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const nav = p => { setPage(p); setMenuOpen(false) }

  const links = [
    { id: 'home',      label: '🏠 Home' },
    { id: 'analytics', label: '📊 Analytics' },
    { id: 'faq',       label: '❓ FAQ' },
    { id: 'about',     label: 'ℹ️ About' },
    { id: 'contact',   label: '📩 Contact' },
  ]

  return (
    <nav className="topnav">
      <div className="topnav-inner">
        <div className="logo" onClick={() => nav('home')}>
          <span className="logo-ball">🏀</span>
          <span className="logo-text">Maddest<span>Offers</span></span>
          <span className="logo-by">by Axon Lattice</span>
        </div>

        <div className="topnav-links">
          {links.map(l => (
            <button key={l.id} className={`nav-link ${page === l.id ? 'active' : ''}`} onClick={() => nav(l.id)}>
              {l.label}
            </button>
          ))}
        </div>

        <button className="burger" onClick={() => setMenuOpen(o => !o)} aria-label="Menu">
          <span /><span /><span />
        </button>
      </div>

      <div className={`mobile-menu ${menuOpen ? 'open' : ''}`}>
        {links.map(l => (
          <button key={l.id} className="mob-link" onClick={() => nav(l.id)}>{l.label}</button>
        ))}
      </div>
    </nav>
  )
}
