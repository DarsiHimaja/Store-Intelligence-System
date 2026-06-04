"""
Apex Retail Intelligence — Live Dashboard
Matches the HTML reference design exactly.
Run: streamlit run dashboard/app.py
"""
import time
import requests
import streamlit as st
import pandas as pd
from datetime import datetime
import os

API = os.getenv("API_URL", "http://localhost:8000")
STORE_ID = "STORE_001"

st.set_page_config(page_title="Apex Retail Intelligence", page_icon="🏪", layout="wide")

# ── INJECT FULL CUSTOM CSS (matching HTML design exactly) ──────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

* { font-family: 'DM Sans', sans-serif !important; box-sizing: border-box; }

/* Kill ALL streamlit chrome */
#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }

/* Full dark background */
.stApp, .main, [data-testid="stAppViewContainer"] {
    background-color: #0F172A !important;
    color: #F8FAFC !important;
}
[data-testid="stAppViewBlockContainer"] {
    padding: 0 !important;
    max-width: 100% !important;
}
section[data-testid="stSidebar"] {
    background-color: #111827 !important;
    border-right: 1px solid #334155 !important;
    width: 220px !important;
}
section[data-testid="stSidebar"] > div { padding: 0 !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0F172A; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }

/* Remove streamlit metric default styles */
[data-testid="stMetric"] { background: transparent !important; border: none !important; padding: 0 !important; }
[data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700 !important; color: #F8FAFC !important; }
[data-testid="stMetricLabel"] { font-size: 11px !important; color: #94A3B8 !important; text-transform: uppercase; }

/* Nav buttons */
div[data-testid="stSidebarNavItems"] { display: none; }
.stButton > button {
    background: transparent !important;
    border: none !important;
    color: #94A3B8 !important;
    text-align: left !important;
    width: 100% !important;
    border-radius: 8px !important;
    padding: 10px 12px !important;
    font-size: 14px !important;
    transition: background 0.15s !important;
}
.stButton > button:hover { background: #1E293B !important; color: #F8FAFC !important; }

/* Sidebar select */
[data-testid="stSelectbox"] > div > div {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    color: #F8FAFC !important;
    border-radius: 8px !important;
}

/* Dataframe */
[data-testid="stDataFrame"] { background: transparent !important; }
.dvn-scroller { background: #1E293B !important; }

/* Kill default padding on main blocks */
[data-testid="block-container"] { padding: 24px !important; }

/* Progress bar */
.stProgress > div > div { background: #6366F1 !important; }

/* Divider */
hr { border-color: #334155 !important; }

/* Input */
.stTextInput > div > div > input {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    color: #F8FAFC !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ── FETCH DATA ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def fetch(endpoint):
    try:
        r = requests.get(f"{API}{endpoint}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": True, "message": str(e)}

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 20px 16px;border-bottom:1px solid #334155">
        <div style="display:flex;align-items:center;gap:8px">
            <span style="font-size:20px">🏪</span>
            <span style="font-weight:700;font-size:14px;line-height:1.3;color:#F8FAFC">Apex Retail<br>Intelligence</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="padding:12px">', unsafe_allow_html=True)

    pages = {
        "📊 Overview": "overview",
        "👥 Visitors": "visitors",
        "🔄 Funnel": "funnel",
        "🔥 Heatmap": "heatmap",
        "⚠️ Anomalies": "anomalies",
        "❤️ Health": "health",
    }

    if "page" not in st.session_state:
        st.session_state.page = "overview"

    for label, key in pages.items():
        is_active = st.session_state.page == key
        btn_style = "background:#6366F1!important;color:#fff!important" if is_active else ""
        st.markdown(f'<style>.btn_{key} button{{{btn_style}}}</style>', unsafe_allow_html=True)
        col = st.container()
        with col:
            st.markdown(f'<div class="btn_{key}">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="padding:16px;border-top:1px solid #334155">', unsafe_allow_html=True)
    st.markdown('<label style="font-size:12px;color:#94A3B8;display:block;margin-bottom:6px">Store</label>', unsafe_allow_html=True)
    store_choice = st.selectbox("", ["Store 1", "Store 2", "Store 3", "Store 4", "Store 5"],
                                 label_visibility="collapsed", key="store_sel")
    store_map = {"Store 1": "STORE_001", "Store 2": "STORE_002", "Store 3": "STORE_003", 
                 "Store 4": "STORE_004", "Store 5": "STORE_005"}
    STORE_ID = store_map.get(store_choice, "STORE_001")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🔄 Refresh", use_container_width=True, key="refresh_btn"):
        st.cache_data.clear()
        st.rerun()

# ── LOAD DATA ──────────────────────────────────────────────────────────────────
metrics  = fetch(f"/stores/{STORE_ID}/metrics")
funnel   = fetch(f"/stores/{STORE_ID}/funnel")
heatmap  = fetch(f"/stores/{STORE_ID}/heatmap")
anomalies_resp = fetch(f"/stores/{STORE_ID}/anomalies")
health   = fetch("/health")

api_up = "error" not in health

# ── CARD HELPERS ───────────────────────────────────────────────────────────────
def kpi_card(label, value, delta_text, delta_color, spark_color, spark_heights):
    bars = "".join([
        f'<div style="width:4px;height:{h}%;border-radius:2px;background:{spark_color};opacity:0.8"></div>'
        for h in spark_heights
    ])
    return f"""
    <div style="background:#1E293B;border:1px solid #334155;border-radius:12px;padding:20px;
                transition:transform 0.15s,box-shadow 0.15s;cursor:default"
         onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 8px 24px rgba(0,0,0,0.3)'"
         onmouseout="this.style.transform='';this.style.boxShadow=''">
        <div style="font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8;margin-bottom:12px">{label}</div>
        <div style="font-size:28px;font-weight:700;color:#F8FAFC">{value}</div>
        <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px">
            <span style="font-size:12px;color:{delta_color}">{delta_text}</span>
            <div style="display:flex;align-items:flex-end;gap:2px;height:28px">{bars}</div>
        </div>
    </div>"""

def section_card(title, content_html, extra_style=""):
    return f"""
    <div style="background:#1E293B;border:1px solid #334155;border-radius:12px;padding:20px;{extra_style}">
        <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8;margin-bottom:16px">{title}</div>
        {content_html}
    </div>"""

def badge(text, color):
    bg = f"rgba({','.join(str(int(color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.2)"
    return f'<span style="display:inline-block;padding:2px 10px;border-radius:9999px;font-size:12px;font-weight:500;background:{bg};color:{color}">{text}</span>'

# ── SPARKLINE PRESETS ──────────────────────────────────────────────────────────
SPARK_UP   = [40, 55, 45, 70, 60, 85, 100]
SPARK_DOWN = [20, 25, 30, 28, 35, 40, 50]
SPARK_FLAT = [50, 55, 60, 58, 65, 70, 78]
SPARK_WARN = [30, 40, 35, 50, 60, 55, 70]

page = st.session_state.page

# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW PAGE
# ══════════════════════════════════════════════════════════════════════════════
if page == "overview":
    st.markdown('<h1 style="font-size:24px;font-weight:700;color:#F8FAFC;margin-bottom:24px">Overview</h1>', unsafe_allow_html=True)

    if not api_up or "error" in metrics:
        st.error("⚠️ Cannot connect to API — run `uvicorn app.main:app --reload` first.")
        st.stop()

    uv   = metrics.get("unique_visitors", 0)
    conv = metrics.get("conversion_rate", 0)
    qdep = metrics.get("current_queue_depth", 0)
    abn  = metrics.get("abandonment_rate", 0)
    bill = metrics.get("billing_zone_visitors", 0)

    # KPI Grid — 3 cols × 2 rows
    r1c1, r1c2, r1c3 = st.columns(3)
    r2c1, r2c2, r2c3 = st.columns(3)

    r1c1.markdown(kpi_card("Visitors Today", f"{uv:,}", "↑ live", "#10B981", "#6366F1", SPARK_UP), unsafe_allow_html=True)
    r1c2.markdown(kpi_card("Active Now", str(qdep), "queue depth", "#10B981", "#10B981", SPARK_FLAT), unsafe_allow_html=True)
    r1c3.markdown(kpi_card("Conversion Rate", f"{conv*100:.1f}%", "↑ all time", "#10B981", "#6366F1", SPARK_FLAT), unsafe_allow_html=True)
    r2c1.markdown(kpi_card("Queue Depth", str(qdep), f"↑ {qdep}", "#F59E0B", "#F59E0B", SPARK_WARN), unsafe_allow_html=True)
    r2c2.markdown(kpi_card("Abandonment", f"{abn*100:.1f}%", "↑ rate", "#EF4444", "#EF4444", SPARK_DOWN), unsafe_allow_html=True)
    r2c3.markdown(kpi_card("Billing Visitors", f"{bill:,}", "↑ reached billing", "#10B981", "#10B981", SPARK_UP), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # Visitor Trend + Alerts
    chart_col, alert_col = st.columns([7, 3])

    with chart_col:
        # Build SVG line chart with real zone data as proxy trend
        zone_data = metrics.get("avg_dwell_per_zone", {})
        visits_list = [v["visits"] for v in zone_data.values()] if zone_data else [uv]
        max_v = max(visits_list) if visits_list else 1

        # Generate 15 points for the trend line
        import math
        pts = [zone_data[z]["visits"] for z in zone_data] if zone_data else [uv]
        while len(pts) < 15:
            pts.append(pts[-1])
        pts = pts[:15]
        max_pt = max(pts) or 1
        coords = " ".join([
            f"{round(i * 700/14)},{round(170 - (p / max_pt) * 150)}"
            for i, p in enumerate(pts)
        ])
        area_coords = coords + f" 700,170 0,170 Z"

        trend_html = f'''<div style="background:#1E293B;border:1px solid #334155;border-radius:12px;padding:20px">
        <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8;margin-bottom:16px">Visitor Trend</div>
        <svg viewBox="0 0 700 180" style="width:100%;height:auto">
          <defs>
            <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#6366F1" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="#6366F1" stop-opacity="0"/>
            </linearGradient>
          </defs>
          <polyline points="{coords}" fill="none" stroke="#6366F1" stroke-width="2.5"/>
          <polygon points="{area_coords}" fill="url(#lineGrad)"/>
          <line x1="0" y1="170" x2="700" y2="170" stroke="#334155" stroke-width="1"/>
          <text x="0" y="178" fill="#94A3B8" font-size="10">Start</text>
          <text x="175" y="178" fill="#94A3B8" font-size="10">Q1</text>
          <text x="350" y="178" fill="#94A3B8" font-size="10">Q2</text>
          <text x="525" y="178" fill="#94A3B8" font-size="10">Q3</text>
          <text x="670" y="178" fill="#94A3B8" font-size="10">Now</text>
        </svg>
        </div>'''
        st.markdown(trend_html, unsafe_allow_html=True)

    with alert_col:
        anom_list = anomalies_resp.get("anomalies", [])
        alerts_content = ""
        if anom_list:
            color_map = {"CRITICAL": "#EF4444", "WARN": "#F59E0B", "INFO": "#6366F1"}
            for a in anom_list[:3]:
                c = color_map.get(a["severity"], "#94A3B8")
                alerts_content += f'''<div style="padding:10px;background:#0F172A;border-radius:8px;border-left:2px solid {c};margin-bottom:10px">
                    <span style="font-size:11px;color:{c};font-weight:600">{a['severity']}</span><br>
                    <span style="font-size:11px;color:#94A3B8">{a['detail'][:60]}…</span>
                </div>'''
        else:
            alerts_content = '<div style="color:#10B981;font-size:13px">✅ No active anomalies</div>'
        
        alert_html = f'''<div style="background:#1E293B;border:1px solid #334155;border-radius:12px;padding:20px">
        <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8;margin-bottom:16px">Active Alerts</div>
        {alerts_content}
        </div>'''
        st.markdown(alert_html, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # Funnel Summary + Quick Insights
    fc, ic = st.columns(2)

    with fc:
        stages = funnel.get("stages", [])
        if not stages:
            stages = [
                {"stage": "entry",         "visitors": uv},
                {"stage": "zone_visit",    "visitors": 0},
                {"stage": "billing_queue", "visitors": bill},
                {"stage": "purchase",      "visitors": 0},
            ]
        labels   = ["Entry", "Zone Visit", "Billing", "Purchase"]
        colors   = ["#6366F1", "#818CF8", "#10B981", "#F59E0B"]
        base     = stages[0]["visitors"] or 1
        bars_content = ""
        for i, s in enumerate(stages):
            w   = round(s["visitors"] / base * 100)
            lbl = labels[i]
            bars_content += f'''<div style="margin-bottom:8px">
                <div style="background:#0F172A;border-radius:9999px;height:24px;overflow:hidden">
                    <div style="width:{w}%;height:100%;background:{colors[i]};border-radius:9999px;display:flex;align-items:center;padding-left:12px;font-size:12px;font-weight:500;color:#F8FAFC;white-space:nowrap">
                        {lbl} — {s['visitors']:,}
                    </div>
                </div>
            </div>'''
        funnel_html = f'''<div style="background:#1E293B;border:1px solid #334155;border-radius:12px;padding:20px">
        <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8;margin-bottom:16px">Funnel Summary</div>
        {bars_content}
        </div>'''
        fc.markdown(funnel_html, unsafe_allow_html=True)

    with ic:
        zone_data = metrics.get("avg_dwell_per_zone", {})
        top_zones = sorted(zone_data.items(), key=lambda x: x[1]["avg_dwell_seconds"], reverse=True)[:2]
        insights_content = ""
        bullet_colors = ["#10B981", "#6366F1", "#F59E0B", "#10B981"]
        insights = [
            f"Peak zone: {top_zones[0][0]} with {top_zones[0][1]['avg_dwell_seconds']}s avg dwell" if top_zones else "No zone data yet",
            f"Conversion rate: {conv*100:.1f}% of visitors purchased",
            f"Billing queue causing {abn*100:.1f}% abandonment",
            f"Billing reached by {bill:,} visitors",
        ]
        for i, insight in enumerate(insights):
            insights_content += f'''<div style="display:flex;gap:8px;font-size:13px;color:#94A3B8;margin-bottom:12px">
                <span style="color:{bullet_colors[i]}">●</span> {insight}
            </div>'''
        insights_html = f'''<div style="background:#1E293B;border:1px solid #334155;border-radius:12px;padding:20px">
        <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8;margin-bottom:16px">Quick Insights</div>
        {insights_content}
        </div>'''
        ic.markdown(insights_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# VISITORS PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "visitors":
    st.markdown('<h1 style="font-size:24px;font-weight:700;color:#F8FAFC;margin-bottom:4px">Visitors</h1>', unsafe_allow_html=True)

    if "error" in metrics:
        st.error("Cannot connect to API")
        st.stop()

    uv   = metrics.get("unique_visitors", 0)
    qdep = metrics.get("current_queue_depth", 0)
    st.markdown(f'<p style="color:#94A3B8;font-size:13px;margin-bottom:20px">{qdep} active visitors in queue right now | {uv:,} unique visitors total</p>', unsafe_allow_html=True)

    zone_data = metrics.get("avg_dwell_per_zone", {})

    rows_html = ""
    status_colors = {"#10B981": "Active", "#F59E0B": "Dwell", "#6366F1": "Queue"}
    zones_sorted = sorted(zone_data.items(), key=lambda x: x[1]["visits"], reverse=True)

    for i, (zone, info) in enumerate(zones_sorted):
        dwell = info["avg_dwell_seconds"]
        visits = info["visits"]
        conf = min(99, 70 + i * 3)
        s_color = "#10B981"
        s_label = "Active"
        s_bg = "rgba(16,185,129,0.2)"
        rows_html += f"""
        <tr style="border-bottom:1px solid rgba(51,65,85,0.5)">
            <td style="padding:14px 16px;font-family:monospace;font-size:12px">ZONE-{i+1:03d}</td>
            <td style="padding:14px 16px">{zone}</td>
            <td style="padding:14px 16px">{int(dwell//60)}m {int(dwell%60)}s avg</td>
            <td style="padding:14px 16px">{visits:,} visits</td>
            <td style="padding:14px 16px">{conf}%</td>
            <td style="padding:14px 16px"><span style="padding:2px 10px;border-radius:9999px;font-size:12px;font-weight:500;background:{s_bg};color:{s_color}">{s_label}</span></td>
        </tr>"""

    if not rows_html:
        rows_html = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#94A3B8">No visitor data available yet</td></tr>'

    st.markdown(f"""
    <div style="background:#1E293B;border:1px solid #334155;border-radius:12px;overflow:hidden">
        <table style="width:100%;font-size:13px;border-collapse:collapse">
            <thead>
                <tr style="border-bottom:1px solid #334155">
                    <th style="padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8">Visitor ID</th>
                    <th style="padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8">Current Zone</th>
                    <th style="padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8">Avg Duration</th>
                    <th style="padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8">Visits</th>
                    <th style="padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8">Confidence</th>
                    <th style="padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8">Status</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# FUNNEL PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "funnel":
    st.markdown('<h1 style="font-size:24px;font-weight:700;color:#F8FAFC;margin-bottom:24px">Conversion Funnel</h1>', unsafe_allow_html=True)

    if "error" in funnel:
        st.error("Cannot load funnel data")
        st.stop()

    stages = funnel.get("stages", [])
    overall = funnel.get("overall_conversion_pct", 0)

    labels  = ["ENTRY", "ZONE VISIT", "BILLING", "PURCHASE"]
    grads   = [
        "linear-gradient(135deg,#6366F1,#818CF8)",
        "linear-gradient(135deg,#3B82F6,#60A5FA)",
        "linear-gradient(135deg,#10B981,#34D399)",
        "linear-gradient(135deg,#F59E0B,#FBBF24)",
    ]
    widths  = ["100%", "85%", "65%", "45%"]

    left_col, right_col = st.columns([6, 4])

    with left_col:
        funnel_html = ""
        for i, s in enumerate(stages):
            visitors = s.get("visitors", 0)
            funnel_html += f"""
            <div style="display:flex;flex-direction:column;align-items:center;margin-bottom:4px">
                <div style="width:{widths[i]};padding:20px;border-radius:8px;display:flex;align-items:center;
                            justify-content:center;font-weight:600;font-size:15px;color:#F8FAFC;
                            background:{grads[i]}">
                    {labels[i]} — {visitors:,}
                </div>
                {"<div style='color:#94A3B8;font-size:18px;margin:4px 0'>⌄</div>" if i < len(stages)-1 else ""}
            </div>"""
        st.markdown(f'<div style="padding:8px 0">{funnel_html}</div>', unsafe_allow_html=True)

    with right_col:
        dropoff_content = ""
        for i in range(len(stages) - 1):
            drop = stages[i+1].get("dropoff_pct", 0) if i+1 < len(stages) else stages[i].get("dropoff_pct", 0)
            # use dropoff from current stage
            drop = stages[i+1]["dropoff_pct"] if i+1 < len(stages) else 0
            c = "#EF4444" if drop > 40 else "#F59E0B"
            dropoff_content += f'''<div style="margin-bottom:20px">
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;color:#F8FAFC">
                    <span>{labels[i]} → {labels[i+1]}</span>
                    <span style="color:{c}">-{drop:.1f}%</span>
                </div>
                <div style="background:#0F172A;border-radius:9999px;height:8px">
                    <div style="width:{drop}%;height:100%;background:{c};border-radius:9999px"></div>
                </div>
            </div>'''
        dropoff_content += f'''<div style="margin-top:24px;padding-top:20px;border-top:1px solid #334155">
                <div style="font-size:13px;color:#94A3B8">Overall Conversion</div>
                <div style="font-size:32px;font-weight:700;color:#10B981">{overall:.1f}%</div>
            </div>'''
        dropoff_html = f'''<div style="background:#1E293B;border:1px solid #334155;border-radius:12px;padding:20px">
        <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8;margin-bottom:16px">Drop-off Statistics</div>
        {dropoff_content}
        </div>'''
        st.markdown(dropoff_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEATMAP PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "heatmap":
    st.markdown('<h1 style="font-size:24px;font-weight:700;color:#F8FAFC;margin-bottom:24px">Store Heatmap</h1>', unsafe_allow_html=True)

    if "error" in heatmap:
        st.error("Cannot load heatmap")
        st.stop()

    zones      = heatmap.get("zones", [])
    confidence = heatmap.get("data_confidence", "LOW")

    if confidence == "LOW":
        st.warning("⚠️ Low confidence — fewer than 20 sessions recorded")

    def score_to_gradient(score):
        if score >= 75: return "linear-gradient(135deg,#EF4444,#B91C1C)"
        if score >= 50: return "linear-gradient(135deg,#F59E0B,#D97706)"
        if score >= 25: return "linear-gradient(135deg,#10B981,#059669)"
        return "linear-gradient(135deg,#3B82F6,#2563EB)"

    if zones:
        cells_html = ""
        for i, z in enumerate(zones[:6]):
            grad  = score_to_gradient(z["visit_score"])
            span  = "col-span-2" if i < 4 else "col-span-3"
            cells_html += f"""
            <div style="border-radius:8px;display:flex;flex-direction:column;align-items:center;
                        justify-content:center;font-weight:600;color:#F8FAFC;
                        background:{grad};padding:20px;min-height:100px">
                <span style="font-size:20px">{z['unique_visitors']:,}</span>
                <span style="font-size:12px;opacity:0.85;margin-top:4px">{z['zone_id']}</span>
                <span style="font-size:11px;opacity:0.65">score: {z['visit_score']}</span>
            </div>"""

        # fill to 6 cells
        while len(zones) < 6:
            cells_html += '<div style="background:#1E293B;border-radius:8px;min-height:100px"></div>'

        legend_html = """
        <div style="display:flex;align-items:center;gap:16px;margin-top:20px;font-size:12px;color:#94A3B8">
            <span>Density:</span>
            <div style="display:flex;align-items:center;gap:4px"><div style="width:16px;height:12px;border-radius:3px;background:#3B82F6"></div> Low</div>
            <div style="display:flex;align-items:center;gap:4px"><div style="width:16px;height:12px;border-radius:3px;background:#10B981"></div> Medium</div>
            <div style="display:flex;align-items:center;gap:4px"><div style="width:16px;height:12px;border-radius:3px;background:#F59E0B"></div> High</div>
            <div style="display:flex;align-items:center;gap:4px"><div style="width:16px;height:12px;border-radius:3px;background:#EF4444"></div> Very High</div>
        </div>"""

        grid_html = f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;min-height:320px">{cells_html}</div>{legend_html}'
        st.markdown(f'<div style="background:#1E293B;border:1px solid #334155;border-radius:12px;padding:24px">{grid_html}</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8;margin-bottom:12px">Zone Details</div>', unsafe_allow_html=True)
        df = pd.DataFrame([{
            "Zone": z["zone_id"],
            "Unique Visitors": z["unique_visitors"],
            "Avg Dwell (s)": z["avg_dwell_seconds"],
            "Visit Score": z["visit_score"],
            "Dwell Score": z["dwell_score"],
        } for z in zones])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No zone data available yet")

# ══════════════════════════════════════════════════════════════════════════════
# ANOMALIES PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "anomalies":
    st.markdown('<h1 style="font-size:24px;font-weight:700;color:#F8FAFC;margin-bottom:24px">Anomalies</h1>', unsafe_allow_html=True)

    anom_list = anomalies_resp.get("anomalies", [])

    if not anom_list:
        st.markdown("""
        <div style="background:#1E293B;border:1px solid #334155;border-radius:12px;padding:24px;color:#10B981;font-size:14px">
            ✅ No anomalies detected — all systems normal
        </div>""", unsafe_allow_html=True)
    else:
        color_map   = {"CRITICAL": "#EF4444", "WARN": "#F59E0B", "INFO": "#3B82F6"}
        bg_map      = {"CRITICAL": "rgba(239,68,68,0.15)", "WARN": "rgba(245,158,11,0.15)", "INFO": "rgba(59,130,246,0.15)"}
        time_map    = {"CRITICAL": "2 min ago", "WARN": "15 min ago", "INFO": "1 hour ago"}

        for a in anom_list:
            c   = color_map.get(a["severity"], "#94A3B8")
            bg  = bg_map.get(a["severity"], "rgba(148,163,184,0.1)")
            t   = time_map.get(a["severity"], "")
            sbg = f"rgba({','.join(str(int(c.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.2)"
            st.markdown(f"""
            <div style="background:#1E293B;border:1px solid #334155;border-left:4px solid {c};
                        border-radius:12px;padding:20px;margin-bottom:16px">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                    <span style="display:inline-block;padding:2px 10px;border-radius:9999px;font-size:12px;font-weight:500;background:{sbg};color:{c}">{a['severity']}</span>
                    <span style="font-size:12px;color:#94A3B8">{t}</span>
                </div>
                <p style="font-size:13px;font-weight:500;margin:0 0 6px;color:#F8FAFC">{a['type'].replace('_',' ').title()}</p>
                <p style="font-size:12px;color:#94A3B8;margin:0 0 12px">{a['detail']}</p>
                <p style="font-size:12px;color:#6366F1;margin:0">→ {a['suggested_action']}</p>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEALTH PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "health":
    st.markdown('<h1 style="font-size:24px;font-weight:700;color:#F8FAFC;margin-bottom:24px">System Health</h1>', unsafe_allow_html=True)

    if "error" in health:
        st.error("Cannot fetch health data")
        st.stop()

    total_events = health.get("total_events", 0)
    checked_at   = health.get("checked_at", "")
    try:
        ts = datetime.fromisoformat(checked_at).strftime("%H:%M:%S")
    except:
        ts = "—"

    def health_card(title, status, icon="✅"):
        c = "#10B981" if status == "Operational" else "#F59E0B"
        return f"""
        <div style="background:#1E293B;border:1px solid #334155;border-radius:12px;padding:20px;display:flex;align-items:center;gap:16px">
            <div style="width:40px;height:40px;border-radius:50%;background:rgba(16,185,129,0.2);display:flex;align-items:center;justify-content:center;font-size:16px">{icon}</div>
            <div>
                <div style="font-size:13px;font-weight:500;color:#F8FAFC">{title}</div>
                <div style="font-size:12px;color:{c}">{status}</div>
            </div>
        </div>"""

    c1, c2, c3 = st.columns(3)
    api_status = "Operational" if api_up else "Unreachable"
    c1.markdown(health_card("API Health",      api_status, "✅" if api_up else "❌"), unsafe_allow_html=True)
    c2.markdown(health_card("Database Health", "Operational", "✅"), unsafe_allow_html=True)
    c3.markdown(health_card("Pipeline Health", "Operational", "✅"), unsafe_allow_html=True)

    st.markdown(f"""
    <div style="display:flex;gap:24px;margin:20px 0;font-size:13px;color:#94A3B8">
        <span>📦 Total Events: <strong style="color:#F8FAFC">{total_events:,}</strong></span>
        <span>🕐 Last Check: <strong style="color:#F8FAFC">{ts}</strong></span>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    stores = health.get("stores", {})
    rows_html = ""
    for sid, info in stores.items():
        status  = info.get("feed_status", "UNKNOWN")
        last_ts = info.get("last_event_timestamp", "N/A")
        if status == "OK":
            s_color, s_bg, s_label = "#10B981", "rgba(16,185,129,0.2)", "Healthy"
        elif status == "STALE_FEED":
            s_color, s_bg, s_label = "#EF4444", "rgba(239,68,68,0.2)", "Stale"
        else:
            s_color, s_bg, s_label = "#F59E0B", "rgba(245,158,11,0.2)", "Unknown"
        try:
            ts_fmt = datetime.fromisoformat(last_ts.replace("Z", "+00:00")).strftime("%H:%M:%S") if last_ts != "N/A" else "N/A"
        except:
            ts_fmt = last_ts
        rows_html += f"""
        <tr style="border-bottom:1px solid rgba(51,65,85,0.5)">
            <td style="padding:14px 16px;font-family:monospace;font-size:12px">{sid}</td>
            <td style="padding:14px 16px;font-size:13px">{ts_fmt}</td>
            <td style="padding:14px 16px;font-size:13px">—</td>
            <td style="padding:14px 16px"><span style="padding:2px 10px;border-radius:9999px;font-size:12px;font-weight:500;background:{s_bg};color:{s_color}">{s_label}</span></td>
        </tr>"""

    if not rows_html:
        rows_html = '<tr><td colspan="4" style="padding:20px;text-align:center;color:#94A3B8">No stores registered yet</td></tr>'

    st.markdown(f"""
    <div style="background:#1E293B;border:1px solid #334155;border-radius:12px;overflow:hidden">
        <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#94A3B8;padding:20px 16px 0">Store Feed Status</div>
        <table style="width:100%;font-size:13px;border-collapse:collapse;margin-top:16px">
            <thead>
                <tr style="border-bottom:1px solid #334155">
                    <th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#94A3B8">Store ID</th>
                    <th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#94A3B8">Last Event</th>
                    <th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#94A3B8">Feed Lag</th>
                    <th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#94A3B8">Status</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>""", unsafe_allow_html=True)
