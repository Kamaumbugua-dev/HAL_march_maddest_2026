import { useState, useEffect, useRef, useCallback } from 'react'
import ProductCard  from './ProductCard'
import ProductModal from './ProductModal'

const fmt = n => `KES ${Number(n).toLocaleString('en-KE', { minimumFractionDigits: 0 })}`

export default function HomePage() {
  const [query,        setQuery]        = useState('')
  const [category,     setCategory]     = useState('All')
  const [categories,   setCategories]   = useState([])
  const [results,      setResults]      = useState([])
  const [allProducts,  setAllProducts]  = useState([])
  const [featured,     setFeatured]     = useState([])
  const [suggestions,  setSuggestions]  = useState([])
  const [showSugg,     setShowSugg]     = useState(false)
  const [status,       setStatus]       = useState(null)
  const [loading,      setLoading]      = useState(false)
  const [searched,     setSearched]     = useState(false)
  const [totalProducts,setTotalProducts]= useState(0)
  const [modalProduct, setModalProduct] = useState(null)

  const inputRef    = useRef(null)
  const searchRef   = useRef(null)
  const debounceRef = useRef(null)
  const queryRef    = useRef('')
  const categoryRef = useRef('All')

  queryRef.current    = query
  categoryRef.current = category

  useEffect(() => {
    fetch('/api/categories')
      .then(r => r.json())
      .then(data => { setCategories(data); setTotalProducts(data.reduce((s, c) => s + c.cnt, 0)) })
      .catch(console.error)

    fetch('/api/products')
      .then(r => r.json())
      .then(data => {
        setAllProducts(data)
        setFeatured([...data].sort((a, b) => b.new_discount - a.new_discount).slice(0, 6))
      })
      .catch(console.error)

    if (window.innerWidth >= 768) inputRef.current?.focus()

    const clickOff = e => { if (!searchRef.current?.contains(e.target)) setShowSugg(false) }
    document.addEventListener('mousedown', clickOff)
    return () => document.removeEventListener('mousedown', clickOff)
  }, [])

  const executeSearch = useCallback(async (q, cat) => {
    const trimQ  = (q   ?? queryRef.current).trim()
    const useCat = (cat ?? categoryRef.current)

    if (!trimQ && useCat === 'All') {
      setSearched(false); setResults([]); setStatus(null)
      return
    }

    setLoading(true)
    setSearched(true)
    setShowSugg(false)

    try {
      const res  = await fetch('/api/search', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ query: trimQ, category: useCat })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResults(data.results ?? [])
      setStatus(data.in_offer !== null ? { found: data.in_offer, count: data.count, query: trimQ } : null)
    } catch (err) {
      console.error('Search error:', err)
      setStatus({ found: false, count: 0, query: trimQ })
    } finally {
      setLoading(false)
    }
  }, [])

  const debouncedSearch = useCallback((q, cat) => {
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => executeSearch(q, cat), 320)
  }, [executeSearch])

  const handleInput = e => {
    const q = e.target.value
    setQuery(q)
    if (q.length >= 2) {
      const ql  = q.toLowerCase()
      const top = allProducts.filter(p =>
        p.item_name.toLowerCase().includes(ql) ||
        p.brand.toLowerCase().includes(ql)     ||
        p.item_code.includes(ql)
      ).slice(0, 6)
      setSuggestions(top)
      setShowSugg(top.length > 0)
    } else {
      setSuggestions([]); setShowSugg(false)
    }
    debouncedSearch(q, categoryRef.current)
  }

  const handleKeyDown = e => {
    if (e.key === 'Enter')  { clearTimeout(debounceRef.current); executeSearch(query, category) }
    if (e.key === 'Escape') setShowSugg(false)
  }

  const handleSearchClick = () => {
    clearTimeout(debounceRef.current)
    executeSearch(queryRef.current, categoryRef.current)
  }

  const handleCategory = cat => {
    setCategory(cat); categoryRef.current = cat
    clearTimeout(debounceRef.current)
    executeSearch(queryRef.current, cat)
  }

  const pickSuggestion = name => {
    setQuery(name); queryRef.current = name
    setShowSugg(false)
    clearTimeout(debounceRef.current)
    executeSearch(name, categoryRef.current)
  }

  const clearSearch = () => {
    clearTimeout(debounceRef.current)
    setQuery(''); setCategory('All')
    queryRef.current = ''; categoryRef.current = 'All'
    setResults([]); setStatus(null); setSearched(false); setShowSugg(false)
    inputRef.current?.focus()
  }

  // Split results: exact match (score >= 82) vs related
  const exactMatches  = results.filter(r => r.score >= 82)
  const relatedItems  = results.filter(r => r.score <  82)

  return (
    <>
      {modalProduct && <ProductModal product={modalProduct} onClose={() => setModalProduct(null)} />}

      {/* HERO */}
      <section className="hero">
        <div className="hero-bg-shapes">
          <div className="shape s1" /><div className="shape s2" /><div className="shape s3" />
        </div>
        <div className="hero-content">
          <div className="hero-badge">🏀 MADDEST OFFERS 2025</div>
          <h1 className="hero-title">
            Find Your<br /><span className="gradient-text">Axon Lattice Deal</span>
          </h1>
          <p className="hero-sub">
            Type a model name or item code to instantly check if it's in our<br />
            Maddest Offers — up to <strong>47% OFF</strong>.
          </p>

          <div className="search-container" ref={searchRef}>
            <div className="search-box">
              <span className="search-icon">🔍</span>
              <input
                ref={inputRef}
                className="search-input"
                type="text"
                value={query}
                onChange={handleInput}
                onKeyDown={handleKeyDown}
                onFocus={() => suggestions.length > 0 && setShowSugg(true)}
                placeholder="Search model name, item code or brand…"
                autoComplete="off"
                spellCheck={false}
              />
              {query && (
                <button className="search-clear" onClick={clearSearch} aria-label="Clear">✕</button>
              )}
              <button className="search-btn search-btn-glow" onClick={handleSearchClick}>
                🔍 Search
              </button>
            </div>

            {showSugg && suggestions.length > 0 && (
              <div className="suggestions">
                {suggestions.map(p => (
                  <div key={p.item_code} className="sugg-item"
                    onMouseDown={e => { e.preventDefault(); pickSuggestion(p.item_name) }}>
                    <span>{p.category_icon}</span>
                    <span>{p.item_name}</span>
                    <span className="sugg-cat">{p.brand}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="hero-stats">
            <div className="stat-chip"><strong>{totalProducts}</strong> Products on Offer</div>
            <div className="stat-chip"><strong>Up to 47%</strong> Discount</div>
            <div className="stat-chip"><strong>6</strong> Top Brands</div>
          </div>
        </div>
      </section>

      {/* CATEGORY NAV */}
      <section className="cat-section">
        <div className="cat-nav">
          <button className={`cat-btn ${category === 'All' ? 'active' : ''}`} onClick={() => handleCategory('All')}>
            <span className="cat-icon">🛍️</span>
            <span className="cat-name">All Deals</span>
          </button>
          {categories.map(c => (
            <button key={c.category}
              className={`cat-btn ${category === c.category ? 'active' : ''}`}
              onClick={() => handleCategory(c.category)}>
              <span className="cat-icon">{c.category_icon}</span>
              <span className="cat-name">{c.category}</span>
              <span className="cat-count">{c.cnt}</span>
            </button>
          ))}
        </div>
      </section>

      {/* RESULTS */}
      <section className="results-section">

        {/* Loading animation */}
        {loading && (
          <div className="search-loading">
            <div className="search-pulse">
              <div className="pulse-ring" />
              <div className="pulse-ring" style={{ animationDelay: '.15s' }} />
              <div className="pulse-ring" style={{ animationDelay: '.3s' }} />
              <span className="pulse-icon">🔍</span>
            </div>
            <p className="search-loading-text">Scanning the Maddest Offers…</p>
          </div>
        )}

        {/* NOT ON OFFER */}
        {!loading && searched && results.length === 0 && (
          <div className="not-on-offer">
            <div className="not-offer-badge">❌ SORRY, ITEM NOT ON OFFER</div>
            <h3 className="not-offer-title">
              {status?.query ? `"${status.query}"` : 'This item'} is not in the Maddest Offers
            </h3>
            <p className="not-offer-sub">
              This product isn't part of the current promotion. Browse the categories below for available deals,
              or ask Steve for alternatives!
            </p>
            <div className="not-offer-actions">
              <button className="btn-primary" onClick={clearSearch}>Browse All Deals</button>
              <button className="btn-outline" onClick={() => document.querySelector('.steve-fab')?.click()}>
                🤖 Ask Steve for alternatives
              </button>
            </div>
            <div className="not-offer-cats">
              <p>Try searching in these categories:</p>
              <div className="cat-chips">
                {categories.slice(0, 6).map(c => (
                  <button key={c.category} className="cat-chip-btn"
                    onClick={() => { clearSearch(); handleCategory(c.category) }}>
                    {c.category_icon} {c.category}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* EXACT MATCH — ACTIVE */}
        {!loading && searched && exactMatches.length > 0 && (
          <div className="active-section">
            <div className="active-header">
              <span className="active-badge">● ACTIVE</span>
              <h2 className="active-title">
                {exactMatches.length === 1 ? 'Exact Match Found' : `${exactMatches.length} Exact Matches Found`}
              </h2>
              <p className="active-sub">This item is on the Maddest Offer! Click the card for full details.</p>
            </div>
            <div className="products-grid">
              {exactMatches.map((item, i) => (
                <ProductCard
                  key={item.product.item_code + i}
                  product={item.product}
                  score={item.score}
                  delay={i}
                  isExact
                  onClick={() => setModalProduct(item.product)}
                />
              ))}
            </div>
          </div>
        )}

        {/* RELATED RESULTS */}
        {!loading && searched && relatedItems.length > 0 && (
          <div className="related-section">
            <h3 className="related-title">
              {exactMatches.length > 0 ? '📦 Related Products' : `📦 ${relatedItems.length} Results Found`}
            </h3>
            <div className="products-grid">
              {relatedItems.map((item, i) => (
                <ProductCard
                  key={item.product.item_code + i}
                  product={item.product}
                  score={item.score}
                  delay={i}
                  onClick={() => setModalProduct(item.product)}
                />
              ))}
            </div>
          </div>
        )}

        {/* WELCOME / FEATURED */}
        {!searched && !loading && (
          <div className="welcome-state">
            <h2 className="section-title">🔥 Hottest Deals Right Now</h2>
            <p className="section-sub">Top picks sorted by biggest discount — click any card to see full details:</p>
            <div className="products-grid">
              {featured.map((p, i) => (
                <ProductCard key={p.item_code} product={p} score={100} delay={i} onClick={() => setModalProduct(p)} />
              ))}
            </div>
          </div>
        )}

      </section>
    </>
  )
}
