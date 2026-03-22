import { useState } from 'react'
import Navbar        from './components/Navbar'
import HomePage      from './components/HomePage'
import AnalyticsPage from './components/AnalyticsPage'
import FAQPage       from './components/FAQPage'
import AboutPage     from './components/AboutPage'
import ContactPage   from './components/ContactPage'
import SteveBot      from './components/SteveBot'

export default function App() {
  const [page, setPage] = useState('home')

  return (
    <>
      <Navbar page={page} setPage={setPage} />
      {page === 'home'      && <HomePage />}
      {page === 'analytics' && <AnalyticsPage />}
      {page === 'faq'       && <FAQPage />}
      {page === 'about'     && <AboutPage />}
      {page === 'contact'   && <ContactPage />}
      <SteveBot />
      <footer className="site-footer">
        <p><strong>Maddest Offers 2025</strong> &mdash; Axon Lattice Internal Deal Finder</p>
        <p className="footer-sub">All prices in Kenyan Shillings (KES). Offers valid while stocks last.</p>
      </footer>
    </>
  )
}
