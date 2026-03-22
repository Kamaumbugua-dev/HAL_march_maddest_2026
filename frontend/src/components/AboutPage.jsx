export default function AboutPage() {
  const stats = [
    { val: '38+', label: 'Products on Offer' },
    { val: '47%', label: 'Max Discount' },
    { val: '6',   label: 'Top Brands' },
    { val: '11',  label: 'Categories' },
  ]

  const brands = [
    { name: 'LG',          desc: 'Premium fridges, TVs, washing machines & washer-dryers', icon: '🌟' },
    { name: 'Hisense',     desc: 'Best value range — fridges, TVs, microwaves & washers',   icon: '💡' },
    { name: 'Von',         desc: 'Local favourite — cookers, fridges, washers & more',       icon: '🏠' },
    { name: 'NutriCook',   desc: 'Up to 47% off air fryers — the biggest deal in the offer',icon: '🍳' },
    { name: 'Nutri Bullet',desc: 'High-performance blenders',                                icon: '🥤' },
    { name: 'Simfer',      desc: 'Quality cookers and kitchen appliances',                   icon: '🔥' },
  ]

  return (
    <>
      <section className="inner-hero">
        <div className="inner-hero-content">
          <div className="hero-badge">ℹ️ ABOUT US</div>
          <h1 className="inner-title">Axon Lattice<br /><span className="gradient-text">Maddest Offers</span></h1>
          <p className="inner-sub">An internal staff portal for finding the best appliance deals in the promotion.</p>
        </div>
      </section>

      <section className="inner-body">

        {/* Stats */}
        <div className="about-stats">
          {stats.map(s => (
            <div className="about-stat" key={s.label}>
              <div className="about-stat-val">{s.val}</div>
              <div className="about-stat-label">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Mission */}
        <div className="about-card">
          <h2 className="about-section-title">🎯 What is Maddest Offers?</h2>
          <p>
            Maddest Offers is <strong>Axon Lattice's</strong> flagship internal promotion — a curated selection of top
            appliances offered to staff at heavily discounted prices. The portal was built to make it easy for any team
            member to quickly check whether a specific product is part of the offer, view pricing details, and compare
            savings across categories.
          </p>
          <p style={{ marginTop: 14 }}>
            With discounts ranging from <strong>17% to 47% off</strong>, this promotion represents exceptional value
            across refrigerators, TVs, washing machines, air fryers, microwaves and more.
          </p>
        </div>

        {/* How it works */}
        <div className="about-card">
          <h2 className="about-section-title">⚙️ How the Portal Works</h2>
          <div className="how-steps">
            {[
              { step: '1', title: 'Search', desc: 'Type any model name, item code, or brand in the search bar.' },
              { step: '2', title: 'Discover', desc: 'Instantly see if the item is ACTIVE in the offer with pricing details.' },
              { step: '3', title: 'Compare', desc: 'Browse by category or ask Steve for smart deal suggestions.' },
              { step: '4', title: 'Act', desc: 'Note the promo price and savings, then contact procurement to purchase.' },
            ].map(s => (
              <div className="how-step" key={s.step}>
                <div className="how-step-num">{s.step}</div>
                <div>
                  <strong>{s.title}</strong>
                  <p>{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Brands */}
        <div className="about-card">
          <h2 className="about-section-title">🏷️ Featured Brands</h2>
          <div className="brands-grid">
            {brands.map(b => (
              <div className="brand-card" key={b.name}>
                <div className="brand-icon">{b.icon}</div>
                <div className="brand-name">{b.name}</div>
                <div className="brand-desc">{b.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Tech */}
        <div className="about-card about-tech">
          <h2 className="about-section-title">🛠️ Built With</h2>
          <div className="tech-pills">
            {['Python Flask', 'SQLite', 'React 18', 'Vite', 'Chart.js', 'RapidFuzz', 'TF-IDF Search', 'Render / Vercel'].map(t => (
              <span className="tech-pill" key={t}>{t}</span>
            ))}
          </div>
          <p style={{ marginTop: 16, fontSize: '.85rem', color: 'var(--muted)' }}>
            Built for Axon Lattice internal staff use. Pricing data sourced from official March Madness product sheets.
          </p>
        </div>

      </section>
    </>
  )
}
