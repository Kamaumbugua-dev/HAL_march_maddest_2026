const fmt = n => `KES ${Number(n).toLocaleString('en-KE', { minimumFractionDigits: 0 })}`

export default function ProductCard({ product, score, delay, onClick }) {
  const savings = product.sale_rrp - product.new_promo_rrp
  const pct     = Math.min(Math.round(score ?? 100), 100)
  const showBar = score !== undefined && score < 100

  return (
    <div
      className="product-card"
      style={{ animationDelay: `${delay * 0.06}s` }}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={e => { if (e.key === 'Enter') onClick() }}
      aria-label={`View details for ${product.item_name}`}
    >
      {/* Header strip */}
      <div className="card-top">
        <span className="brand-badge">{product.brand}</span>
        <span className="discount-badge">{product.new_discount.toFixed(0)}% OFF</span>
      </div>

      {/* Body */}
      <div className="card-body">
        <div className="item-code"># {product.item_code}</div>
        <div className="product-name">{product.item_name}</div>
        <div className="prices">
          <span className="original-price">{fmt(product.sale_rrp)}</span>
          <span className="promo-price">{fmt(product.new_promo_rrp)}</span>
        </div>
        {savings > 0 && (
          <div className="savings-row">
            🎉 Save: <strong>{fmt(savings)}</strong>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="card-footer">
        <span className="category-chip">{product.category_icon} {product.category}</span>
        {showBar ? (
          <div className="match-info">
            Match {pct}%
            <div className="match-bar">
              <div className="match-fill" style={{ width: `${pct}%` }} />
            </div>
          </div>
        ) : (
          <span className="click-hint">👆 Tap for details</span>
        )}
      </div>
    </div>
  )
}
