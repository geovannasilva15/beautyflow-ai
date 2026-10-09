from __future__ import annotations

import streamlit as st


def apply_global_styles() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
    html,body,[class*="css"] {font-family:'DM Sans',sans-serif}
    .stApp {background:#faf8f9;color:#3e3540}
    .block-container {max-width:1480px!important;padding:2rem 2.2rem!important}
    header[data-testid="stHeader"] {background:transparent}
    section[data-testid="stSidebar"] {background:#fff!important;border-right:1px solid #f0e8eb}
    section[data-testid="stSidebar"] * {color:#594c54}
    section[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {background:#fae9ee;border-radius:10px}
    .stButton>button[kind="primary"],.stButton>button {background:#d98c9d!important;color:white!important;border:0!important;border-radius:10px!important;font-weight:600!important;box-shadow:none!important}
    .stButton>button:hover {background:#be7186!important}
    div[data-testid="stMetric"] {background:#fff;border:1px solid #f1e9eb;border-radius:14px;padding:18px;min-height:115px;box-shadow:0 6px 24px rgba(81,44,59,.035)}
    div[data-testid="stMetricLabel"] {color:#827780;font-size:.87rem}
    div[data-testid="stMetricValue"] {color:#382c35;font-family:'Plus Jakarta Sans',sans-serif;font-size:1.75rem;font-weight:800}
    div[data-testid="stVerticalBlockBorderWrapper"] {background:#fff;border:1px solid #f1e9eb!important;border-radius:14px!important;padding:.45rem;box-shadow:0 6px 24px rgba(81,44,59,.035)}
    .bf-eyebrow {font-size:.73rem;letter-spacing:.16em;font-weight:700;color:#bd7b8f;margin-bottom:12px}
    .bf-title {font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;color:#3b2d39;letter-spacing:-.045em;font-size:clamp(1.8rem,3vw,2.5rem);margin:0}
    .bf-subtitle {color:#887d84;font-size:.97rem;margin:.6rem 0 1.5rem}
    h3 {font-family:'Plus Jakarta Sans',sans-serif!important;font-size:1.04rem!important;letter-spacing:-.02em}
    .bf-calendar {display:grid;grid-template-columns:repeat(7,minmax(0,1fr));border-top:1px solid #f2edef;border-left:1px solid #f2edef;overflow:hidden}
    .bf-weekday {text-align:center;background:#fcf8fa;color:#a4979e;font-size:.73rem;font-weight:700;padding:12px 2px;border-right:1px solid #f2edef;border-bottom:1px solid #f2edef}
    .bf-day {min-height:97px;min-width:0;padding:8px 5px;background:white;border-right:1px solid #f2edef;border-bottom:1px solid #f2edef}
    .bf-other-month {background:#fcfbfb;opacity:.5}
    .bf-date {display:inline-flex;align-items:center;justify-content:center;color:#7e7379;font-size:.75rem;height:25px;width:25px;border-radius:50%}
    .bf-today .bf-date {background:#d98c9d;color:white;font-weight:700}
    .bf-event {background:#f5dbe2;color:#8f4961;border-left:3px solid #d98c9d;border-radius:4px;padding:4px;font-size:.64rem;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .bf-event-canceled {background:#f1eef0;color:#a69aa1;text-decoration:line-through;border-radius:4px;padding:4px;font-size:.64rem;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .bf-more {font-size:.63rem;color:#ab7586}
    .bf-appointment {display:flex;flex-direction:column;padding:11px 12px;margin:8px 0;background:#fdf9fa;border:1px solid #f5edf0;border-radius:10px}
    .bf-appointment-time {font-size:.71rem;color:#bc778d;font-weight:700;margin-bottom:4px}
    .bf-appointment strong {font-size:.86rem;color:#493e46}
    .bf-appointment small {font-size:.76rem;color:#948992}
    @media(max-width:850px) {.block-container{padding:1rem!important}.bf-day{min-height:64px;padding:3px}.bf-event{font-size:.55rem;padding:2px}.bf-title{font-size:1.7rem}}
    </style>
    """, unsafe_allow_html=True)


def apply_login_styles() -> None:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {display:none!important}
    .block-container {max-width:540px!important;padding-top:5rem!important}
    .stButton>button {width:100%!important}
    </style>
    """, unsafe_allow_html=True)
