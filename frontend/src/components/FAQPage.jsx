import { useState } from 'react'

const FAQS = [
  {
    q: 'What is the Maddest Offers promotion?',
    a: 'Maddest Offers is Axon Lattice\'s internal promotion featuring deeply discounted appliances from top brands like LG, Hisense, Von, NutriCook, Nutri Bullet and Simfer — with discounts of up to 47% off the regular selling price.'
  },
  {
    q: 'How do I check if my item is on the offer?',
    a: 'Simply type the model name, item code, or brand name in the search bar on the Home page and hit Search. If the item is active in the offer, you\'ll see an "ACTIVE" badge and full deal details. If not, you\'ll see a "SORRY, ITEM NOT ON OFFER" message.'
  },
  {
    q: 'What brands are included in the offer?',
    a: 'The offer includes: LG, Hisense, Von, NutriCook, Nutri Bullet, and Simfer. These cover refrigerators, TVs, washing machines, washer-dryers, microwaves, air fryers, freezers, blenders, cookers, water dispensers, and personal care appliances.'
  },
  {
    q: 'How accurate are the prices shown?',
    a: 'All prices are in Kenyan Shillings (KES) and reflect the current Maddest Offers promotional prices. Original (RRP) and promo prices are both shown so you can see your exact savings. Prices are valid while stocks last.'
  },
  {
    q: 'Can I search by model number?',
    a: 'Yes! You can search by exact model code (e.g. GL-C652HLCM), partial model name (e.g. GL-C652), brand (e.g. LG), or category (e.g. fridge, air fryer). The search handles abbreviations like WM for washing machine and MWO for microwave.'
  },
  {
    q: 'What does the "ACTIVE" badge mean?',
    a: 'The ACTIVE badge (green pulse) means the item you searched for is confirmed on the Maddest Offer. These are exact or very close matches to your search query. Items without the ACTIVE badge are related products that may also interest you.'
  },
  {
    q: 'Who is Steve and what can he do?',
    a: 'Steve is your AI assistant! You can ask him to find deals (e.g. "Find me an LG fridge"), suggest best buys, compare brands, show budget deals, or answer any questions about the promotion. He\'ll search and show you matching products right in the chat.'
  },
  {
    q: 'Are these prices available to all staff?',
    a: 'This portal is for Axon Lattice internal staff only. The deals shown are for the Maddest Offers promotion. Please contact the Procurement or Sales team for purchase procedures and availability.'
  },
  {
    q: 'What if the item I want is not on the offer?',
    a: 'If your item isn\'t in the current offer, you\'ll see a "SORRY, ITEM NOT ON OFFER" message. You can then browse by category to find similar alternatives, or ask Steve to suggest a comparable product that IS on offer.'
  },
  {
    q: 'How do I contact the team?',
    a: 'Use the Contact page in the navigation bar to send us a message. You can reach out for inquiries about pricing, stock availability, purchase procedures, or any issues with the portal.'
  },
]

function Item({ faq, index }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`faq-item ${open ? 'faq-open' : ''}`}>
      <button className="faq-q" onClick={() => setOpen(o => !o)}>
        <span className="faq-num">0{index + 1}</span>
        <span className="faq-q-text">{faq.q}</span>
        <span className="faq-chevron">{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="faq-a">{faq.a}</div>}
    </div>
  )
}

export default function FAQPage() {
  return (
    <>
      <section className="inner-hero">
        <div className="inner-hero-content">
          <div className="hero-badge">❓ FREQUENTLY ASKED QUESTIONS</div>
          <h1 className="inner-title">Got Questions?<br /><span className="gradient-text">We've Got Answers.</span></h1>
          <p className="inner-sub">Everything you need to know about the Maddest Offers portal.</p>
        </div>
      </section>

      <section className="inner-body">
        <div className="faq-list">
          {FAQS.map((f, i) => <Item key={i} faq={f} index={i} />)}
        </div>
        <div className="faq-cta">
          <p>Still have questions?</p>
          <p className="faq-cta-sub">Our team is happy to help — reach out via the Contact page.</p>
        </div>
      </section>
    </>
  )
}
