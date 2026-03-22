import { useEffect, useState } from 'react'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, ArcElement,
  PointElement, LineElement, Title, Tooltip, Legend, Filler
} from 'chart.js'
import { Bar, Doughnut, Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale, LinearScale, BarElement, ArcElement,
  PointElement, LineElement, Title, Tooltip, Legend, Filler
)

// ── Shared colour palette ────────────────────────────────────────────────────
const P = ['#FF6B35','#7B2D8B','#FFD700','#00C851','#00BFFF','#FF4757','#2ED573','#FFA502','#747D8C','#5352ED']

ChartJS.defaults.font.family = 'Poppins'

const fmt = n => `KES ${Number(n).toLocaleString('en-KE')}`

// Wrapper that guarantees the canvas has a stable pixel height
function ChartBox({ children, height = 260 }) {
  return (
    <div style={{ position: 'relative', width: '100%', height: `${height}px` }}>
      {children}
    </div>
  )
}

// ── Chart option presets ─────────────────────────────────────────────────────
const baseOpts = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 600 },
  plugins: { legend: { display: false } },
}

const vertOpts = {
  ...baseOpts,
  scales: {
    x: { grid: { display: false }, ticks: { font: { size: 11 } } },
    y: { beginAtZero: true, grid: { color: '#f0f0f0' }, ticks: { stepSize: 1, font: { size: 11 } } },
  },
}

const horizOpts = {
  ...baseOpts,
  indexAxis: 'y',
  scales: {
    x: { beginAtZero: true, grid: { color: '#f0f0f0' }, ticks: { font: { size: 11 } } },
    y: { grid: { display: false }, ticks: { font: { size: 11 } } },
  },
}

// ── Main component ───────────────────────────────────────────────────────────
export default function AnalyticsPage() {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    fetch('/api/analytics')
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(d  => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  // ── Loading / error states ──────────────────────────────────────────────
  if (loading) return (
    <>
      <AnalyticsHero />
      <div className="spinner-wrap" style={{ padding: '100px 0' }}>
        <div className="spinner" />
        <p>Loading analytics…</p>
      </div>
    </>
  )

  if (error || !data) return (
    <>
      <AnalyticsHero />
      <div style={{ textAlign: 'center', padding: '60px 20px', color: '#721c24' }}>
        <p style={{ fontSize: '2rem', marginBottom: 12 }}>⚠️</p>
        <p><strong>Could not load analytics.</strong></p>
        <p style={{ color: '#888', marginTop: 8 }}>{error || 'Unknown error'}</p>
      </div>
    </>
  )

  // ── Derived values ──────────────────────────────────────────────────────
  const totalProds  = data.category_distribution.reduce((s, c) => s + c.count, 0)
  const topQuery    = data.top_searches[0]?.query || '—'
  const maxDiscount = data.top_discounts[0]?.new_discount ?? 0

  // ── Chart datasets ──────────────────────────────────────────────────────
  const searchBarData = {
    labels:   data.top_searches.map(d => d.query),
    datasets: [{ label: 'Searches', data: data.top_searches.map(d => d.count),
      backgroundColor: P.slice(0, data.top_searches.length), borderRadius: 8, borderSkipped: false }],
  }

  const doughnutData = {
    labels:   data.category_distribution.map(d => `${d.category_icon} ${d.category}`),
    datasets: [{ data: data.category_distribution.map(d => d.count),
      backgroundColor: P, borderWidth: 2, borderColor: '#fff', hoverOffset: 6 }],
  }

  const lineData = {
    labels:   data.daily_searches.map(d => d.day),
    datasets: [{ label: 'Searches', data: data.daily_searches.map(d => d.count),
      borderColor: '#FF6B35', backgroundColor: 'rgba(255,107,53,0.12)',
      fill: true, tension: 0.4, pointBackgroundColor: '#FF6B35', pointRadius: 5 }],
  }

  const catBarData = {
    labels:   data.category_searches.map(d => d.category),
    datasets: [{ label: 'Searches', data: data.category_searches.map(d => d.count),
      backgroundColor: P.slice(2), borderRadius: 8, borderSkipped: false }],
  }

  const doughnutOpts = {
    responsive: true, maintainAspectRatio: false, cutout: '62%',
    animation: { duration: 600 },
    plugins: {
      legend: {
        position: 'right',
        labels: { padding: 12, font: { family: 'Poppins', size: 11 }, usePointStyle: true }
      }
    }
  }

  return (
    <>
      <AnalyticsHero />

      <div className="analytics-body">

        {/* ── KPI Cards ────────────────────────────────────────────────── */}
        <div className="stats-row">
          {[
            { icon: '🔍', val: data.total_searches.toLocaleString(), label: 'Total Searches' },
            { icon: '🏆', val: topQuery, label: 'Top Search Term' },
            { icon: '🛍️', val: totalProds, label: 'Products on Offer' },
            { icon: '🔥', val: maxDiscount ? `${maxDiscount.toFixed(0)}%` : '—', label: 'Max Discount' },
          ].map((k, i) => (
            <div className="kpi-card" key={i}>
              <div className="kpi-icon">{k.icon}</div>
              <div className="kpi-val" style={String(k.val).length > 8 ? { fontSize: '1.2rem' } : {}}>
                {k.val}
              </div>
              <div className="kpi-label">{k.label}</div>
            </div>
          ))}
        </div>

        {/* ── Charts Grid ──────────────────────────────────────────────── */}
        <div className="charts-grid">

          {/* Top searches — wide bar */}
          <div className="chart-card wide">
            <div className="chart-title">🔍 Most Searched Terms</div>
            {data.top_searches.length > 0
              ? <ChartBox><Bar data={searchBarData} options={vertOpts} /></ChartBox>
              : <div className="no-data">No searches yet — start searching on the Home page!</div>
            }
          </div>

          {/* Products by category — doughnut */}
          <div className="chart-card">
            <div className="chart-title">🥧 Products by Category</div>
            <ChartBox height={300}>
              <Doughnut data={doughnutData} options={doughnutOpts} />
            </ChartBox>
          </div>

          {/* Daily activity — line */}
          <div className="chart-card">
            <div className="chart-title">📈 Search Activity</div>
            {data.daily_searches.length > 0
              ? <ChartBox><Line data={lineData} options={vertOpts} /></ChartBox>
              : <div className="no-data">No activity recorded yet.</div>
            }
          </div>

          {/* Category searches — horizontal bar */}
          <div className="chart-card">
            <div className="chart-title">📂 Searches by Category</div>
            {data.category_searches.length > 0
              ? <ChartBox><Bar data={catBarData} options={horizOpts} /></ChartBox>
              : <div className="no-data">No category filter searches yet.</div>
            }
          </div>

        </div>

        {/* ── Top Discounts Table ───────────────────────────────────────── */}
        <div className="chart-card" style={{ marginBottom: 20 }}>
          <div className="chart-title">🔥 Top Discounts in the Offer</div>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th><th>Product</th><th>Original</th>
                  <th>Promo Price</th><th>Discount</th><th>Savings</th>
                </tr>
              </thead>
              <tbody>
                {data.top_discounts.map((p, i) => (
                  <tr key={i}>
                    <td><span className="rank-badge">#{i + 1}</span></td>
                    <td>
                      <div className="prod-name">{p.category_icon} {p.item_name}</div>
                      <div className="brand-tag">{p.brand}</div>
                    </td>
                    <td className="price-old">{fmt(p.sale_rrp)}</td>
                    <td className="price-new">{fmt(p.new_promo_rrp)}</td>
                    <td><span className="disc-pill">{p.new_discount.toFixed(0)}% OFF</span></td>
                    <td className="savings-col">{fmt(p.sale_rrp - p.new_promo_rrp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Zero-result searches ──────────────────────────────────────── */}
        {data.zero_results?.length > 0 && (
          <div className="chart-card">
            <div className="chart-title">❌ Frequently Not Found</div>
            <p style={{ fontSize: '.82rem', color: '#888', marginBottom: 12 }}>
              These searches returned no results — possible gaps in the offer.
            </p>
            <ul className="zero-list">
              {data.zero_results.map((z, i) => (
                <li key={i}>
                  <span className="zero-query">"{z.query}"</span>
                  <span className="zero-count">{z.count}×</span>
                </li>
              ))}
            </ul>
          </div>
        )}

      </div>
    </>
  )
}

function AnalyticsHero() {
  return (
    <section className="analytics-hero">
      <h1 className="analytics-title">📊 Search Analytics</h1>
      <p className="analytics-sub">Real-time insights on what Axon Lattice staff are searching for.</p>
    </section>
  )
}
