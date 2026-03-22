import { useEffect } from 'react'

const fmt = n => `KES ${Number(n).toLocaleString('en-KE', { minimumFractionDigits: 0 })}`

export default function ProductModal({ product, onClose }) {
  // Close on Escape key
  useEffect(() => {
    const handle = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handle)
    return () => window.removeEventListener('keydown', handle)
  }, [onClose])

  if (!product) return null

  const savings = product.sale_rrp - product.new_promo_rrp

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal-box">
        {/* Header */}
        <div className="modal-header">
          <button className="modal-close" onClick={onClose}>✕</button>
          <div className="modal-brand-row">
            <span className="modal-brand">{product.brand}</span>
            <span className="modal-discount">{product.new_discount.toFixed(0)}% OFF</span>
          </div>
          <div className="modal-name">{product.item_name}</div>
        </div>

        {/* Body */}
        <div className="modal-body">
          {/* Info grid */}
          <div className="modal-grid">
            <div className="info-tile">
              <div className="tile-label">Item Code</div>
              <div className="tile-value" style={{ fontFamily: 'monospace', color: 'var(--orange)' }}>
                {product.item_code}
              </div>
            </div>
            <div className="info-tile">
              <div className="tile-label">Brand</div>
              <div className="tile-value">{product.brand}</div>
            </div>
            <div className="info-tile">
              <div className="tile-label">Original Price</div>
              <div className="tile-value price-orig">{fmt(product.sale_rrp)}</div>
            </div>
            <div className="info-tile">
              <div className="tile-label">Promo Price</div>
              <div className="tile-value price-promo">{fmt(product.new_promo_rrp)}</div>
            </div>
            <div className="info-tile">
              <div className="tile-label">Discount</div>
              <div className="tile-value" style={{ color: 'var(--orange)', fontSize: '1.4rem' }}>
                {product.new_discount.toFixed(0)}%
              </div>
            </div>
            <div className="info-tile">
              <div className="tile-label">Category</div>
              <div className="tile-value" style={{ fontSize: '0.92rem' }}>
                {product.category_icon} {product.category}
              </div>
            </div>
          </div>

          {/* Savings highlight */}
          <div className="modal-savings-bar">
            <span className="savings-icon">🎉</span>
            <div className="savings-text">
              You save {fmt(savings)}
              <span>That's {product.new_discount.toFixed(0)}% off the regular retail price!</span>
            </div>
          </div>

          {/* Chips */}
          <div className="modal-cat-row">
            <span className="modal-chip">{product.category_icon} {product.category}</span>
            <span className="modal-code-chip"># {product.item_code}</span>
            <span className="modal-chip" style={{ background: 'rgba(255,107,53,.1)', color: 'var(--orange)' }}>
              {product.brand}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
