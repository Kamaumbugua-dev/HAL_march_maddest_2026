import { useState } from 'react'

export default function Navbar({ page, setPage }) {
  const [menuOpen, setMenuOpen] = useState(false)

  const nav = (p) => { setPage(p); setMenuOpen(false) }

  return (
    <nav className="topnav">
      <div className="topnav-inner">
        <div className="logo" onClick={() => nav('home')}>
          <span className="logo-ball">🏀</span>
          <span className="logo-text">Maddest<span>Offers</span></span>
          <span className="logo-by">by Axon Lattice</span>
        </div>

        <div className="topnav-links">
          <button className={`nav-link ${page === 'home' ? 'active' : ''}`} onClick={() => nav('home')}>
            Home
          </button>
          <button className={`nav-link ${page === 'analytics' ? 'active' : ''}`} onClick={() => nav('analytics')}>
            📊 Analytics
          </button>
        </div>

        <button className="burger" onClick={() => setMenuOpen(o => !o)} aria-label="Menu">
          <span /><span /><span />
        </button>
      </div>

      <div className={`mobile-menu ${menuOpen ? 'open' : ''}`}>
        <button className="mob-link" onClick={() => nav('home')}>🏠 Home</button>
        <button className="mob-link" onClick={() => nav('analytics')}>📊 Analytics</button>
      </div>
    </nav>
  )
}
