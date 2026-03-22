import { useState } from 'react'

export default function ContactPage() {
  const [form,    setForm]    = useState({ name: '', email: '', subject: '', message: '' })
  const [sending, setSending] = useState(false)
  const [sent,    setSent]    = useState(false)
  const [error,   setError]   = useState(null)

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault()
    setSending(true); setError(null)
    try {
      const res  = await fetch('https://formspree.io/f/mreywqzb', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body:    JSON.stringify(form)
      })
      const data = await res.json()
      if (res.ok) { setSent(true); setForm({ name: '', email: '', subject: '', message: '' }) }
      else setError(data.error || 'Something went wrong. Please try again.')
    } catch {
      setError('Could not reach the server. Please try again later.')
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      <section className="inner-hero">
        <div className="inner-hero-content">
          <div className="hero-badge">📩 GET IN TOUCH</div>
          <h1 className="inner-title">Contact<br /><span className="gradient-text">Our Team</span></h1>
          <p className="inner-sub">Questions about the offer? Need help with the portal? We're here.</p>
        </div>
      </section>

      <section className="inner-body">
        <div className="contact-layout">

          {/* Info */}
          <div className="contact-info">
            <h2 className="about-section-title">How can we help?</h2>
            <p style={{ color: 'var(--muted)', marginBottom: 24 }}>
              Reach out for any questions about the Maddest Offers promotion, pricing, availability, or portal issues.
            </p>
            {[
              { icon: '📦', title: 'Stock & Availability', desc: 'Ask about specific models, quantities or delivery timelines.' },
              { icon: '💰', title: 'Pricing Queries', desc: 'Clarify promo prices, savings or payment options.' },
              { icon: '🛠️', title: 'Portal Issues', desc: 'Report bugs, missing products or search issues.' },
              { icon: '🤝', title: 'General Enquiries', desc: 'Anything else about the Axon Lattice Maddest Offers.' },
            ].map(c => (
              <div className="contact-info-item" key={c.title}>
                <div className="contact-info-icon">{c.icon}</div>
                <div>
                  <strong>{c.title}</strong>
                  <p>{c.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Form */}
          <div className="contact-form-wrap">
            {sent ? (
              <div className="contact-success">
                <div className="success-icon">✅</div>
                <h3>Message Sent!</h3>
                <p>Thank you for reaching out. Our team will get back to you shortly.</p>
                <button className="btn-primary" onClick={() => setSent(false)}>Send Another</button>
              </div>
            ) : (
              <form className="contact-form" onSubmit={handleSubmit}>
                <h2 className="form-title">Send a Message</h2>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Your Name *</label>
                    <input className="form-input" type="text" required
                      placeholder="Jane Doe"
                      value={form.name} onChange={set('name')} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Email Address *</label>
                    <input className="form-input" type="email" required
                      placeholder="jane@axonlattice.com"
                      value={form.email} onChange={set('email')} />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Subject</label>
                  <select className="form-input" value={form.subject} onChange={set('subject')}>
                    <option value="">Select a subject…</option>
                    <option>Stock & Availability</option>
                    <option>Pricing Query</option>
                    <option>Portal Issue / Bug</option>
                    <option>General Enquiry</option>
                    <option>Other</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Message *</label>
                  <textarea className="form-input form-textarea" required rows={5}
                    placeholder="Tell us what you need…"
                    value={form.message} onChange={set('message')} />
                </div>

                {error && <div className="form-error">⚠️ {error}</div>}

                <button className="btn-primary form-submit" type="submit" disabled={sending}>
                  {sending ? '⏳ Sending…' : '📩 Send Message'}
                </button>
              </form>
            )}
          </div>

        </div>
      </section>
    </>
  )
}
