"""Small presentation helpers; analytical definitions live in analysis.py."""
import streamlit as st

from .config import ROOT


def apply_styles():
    css = (ROOT / "static" / "dashboard.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def hero():
    st.markdown("""
    <section class="hero" aria-label="Dashboard introduction">
      <div class="hero-topline">
        <span class="hero-kicker">OLIST / OPERATIONS ANALYTICS</span>
        <span class="history-badge"><span class="history-dot" aria-hidden="true"></span>Historical data · 2016–2018</span>
      </div>
      <h1 class="hero-title">Deliver better. Know where to start.</h1>
      <p class="hero-description">Explore delivery performance, understand customer experience, and focus your next investigation.</p>
    </section>
    """, unsafe_allow_html=True)


def sidebar_brand():
    st.markdown("""
    <div class="sidebar-brand">
      <span class="brand-icon" aria-hidden="true"><svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="M3 8v9l9 5 9-5V8M12 13v9M7.5 5.5l9 5"/></svg></span>
      <div><div class="brand-name">olist<span style="color:#157b74">.</span></div><div class="brand-subtitle">Delivery Intelligence</div></div>
    </div>
    <div class="filter-label">Cohort filters</div>
    """, unsafe_allow_html=True)


def review_insight(gap, post_gap):
    # Numeric values originate from aggregate queries, not raw review/customer text.
    post_value = f"{post_gap:.1f}" if post_gap == post_gap else "—"
    st.markdown(f"""
    <section class="insight-card" aria-label="Review timing sensitivity">
      <div class="insight-heading"><h2>Review timing changes the story</h2><span class="insight-tag">Sensitivity check</span></div>
      <div class="insight-comparison">
        <div class="insight-measure"><div class="insight-label">All reviewed deliveries</div><div class="insight-value">{gap:.1f} <span>pp gap</span></div></div>
        <div class="insight-measure"><div class="insight-label">Reviews answered after delivery</div><div class="insight-value">{post_value} <span>pp gap</span></div></div>
      </div>
      <p class="insight-note">Poor-review rate for late minus on-time deliveries. Some reviews were submitted before delivery; both comparisons are observational.</p>
    </section>
    """, unsafe_allow_html=True)
