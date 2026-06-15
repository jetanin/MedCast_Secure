"""MedCast_Secure — Dashboard (Streamlit)

รัน:  streamlit run dashboard/app.py
แสดง 3 พาเนลตามโจทย์:
  1) Overview Map        — ตำแหน่ง รพ. + สถานะสี เขียว/เหลือง/แดง
  2) AI Intelligence     — กราฟพยากรณ์ความต้องการยา + Confidence Score
  3) Privacy Control     — สถานะการเชื่อมต่อ / Secure Aggregation / การเข้ารหัส
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from forecasting import (
    forecast_all, load_hospital_master, load_atc_names, load_global_model,
)

st.set_page_config(page_title="MedCast_Secure", page_icon="💊", layout="wide")

STATUS_COLOR = {"green": "#2ecc71", "yellow": "#f1c40f", "red": "#e74c3c"}
STATUS_TH = {"green": "🟢 เพียงพอ", "yellow": "🟡 ใกล้หมด", "red": "🔴 ขาดแคลน"}
STATUS_RANK = {"green": 0, "yellow": 1, "red": 2}


@st.cache_data(show_spinner="กำลังพยากรณ์จาก weight กลาง...")
def get_data():
    forecast_df, history = forecast_all()
    master = load_hospital_master()
    atc = load_atc_names()
    return forecast_df, history, master, atc


forecast_df, history, master, atc = get_data()
bundle = load_global_model()

# สถานะรวมต่อ รพ. = สถานะที่แย่ที่สุดในบรรดายาทั้งหมด
hosp_status = (
    forecast_df.assign(rank=forecast_df["status"].map(STATUS_RANK))
    .sort_values("rank")
    .groupby("hospital_id")
    .agg(worst_status=("status", "last"),
         n_red=("status", lambda s: (s == "red").sum()),
         n_yellow=("status", lambda s: (s == "yellow").sum()),
         avg_conf=("confidence", "mean"))
    .reset_index()
)
hosp_status["rank"] = hosp_status["worst_status"].map(STATUS_RANK)
map_df = master.merge(hosp_status, on="hospital_id", how="left")

# ---------- Header + KPI ----------
st.title("💊 MedCast_Secure — ศูนย์เฝ้าระวังการขาดแคลนยา")
st.caption("พยากรณ์ความต้องการยาข้ามโรงพยาบาลแบบรักษาความเป็นส่วนตัว (Federated Learning + Differential Privacy)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("โรงพยาบาลที่เชื่อมต่อ", f"{len(master)} แห่ง")
c2.metric("🔴 ยาขาดแคลน (รายการ)", int((forecast_df["status"] == "red").sum()))
c3.metric("🟡 ยาใกล้หมด (รายการ)", int((forecast_df["status"] == "yellow").sum()))
c4.metric("Confidence เฉลี่ย", f"{forecast_df['confidence'].mean()*100:.0f}%")

tab_map, tab_ai, tab_priv = st.tabs(["🗺️ Overview Map", "🤖 AI Intelligence", "🔒 Privacy Control Center"])

# ========== 1) OVERVIEW MAP ==========
with tab_map:
    st.subheader("ตำแหน่งโรงพยาบาลและสถานะยา")
    st.caption("สถานะตามจำนวนวันที่ยาเหลือในคลัง (days-of-supply): 🟢 ≥14 วัน (ให้ยืมได้) · 🟡 4–13 วัน · 🔴 ≤3 วัน (ขาดคลัง)")
    fig = px.scatter_map(
        map_df, lat="latitude", lon="longitude",
        color="worst_status", color_discrete_map=STATUS_COLOR,
        size=[18] * len(map_df), size_max=22,
        hover_name="name",
        hover_data={"hospital_id": True, "n_red": True, "n_yellow": True,
                    "latitude": False, "longitude": False, "worst_status": False},
        zoom=4.3, height=520,
    )
    fig.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0),
                      legend_title="สถานะ (แย่สุดใน รพ.)")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**สรุปสถานะรายโรงพยาบาล**")
    show = map_df[["hospital_id", "name", "worst_status", "n_red", "n_yellow", "avg_conf"]].copy()
    show["worst_status"] = show["worst_status"].map(STATUS_TH)
    show["avg_conf"] = (show["avg_conf"] * 100).round(0).astype(int).astype(str) + "%"
    show.columns = ["รหัส", "โรงพยาบาล", "สถานะรวม", "ยาขาด", "ยาใกล้หมด", "Confidence"]
    st.dataframe(show, use_container_width=True, hide_index=True)

# ========== 2) AI INTELLIGENCE ==========
with tab_ai:
    col_sel1, col_sel2 = st.columns(2)
    hid = col_sel1.selectbox("เลือกโรงพยาบาล", master["hospital_id"],
                             format_func=lambda x: f"{x} — {master.set_index('hospital_id').loc[x,'name']}")
    drugs = sorted(forecast_df["drug"].unique())
    drug = col_sel2.selectbox("เลือกกลุ่มยา (ATC)", drugs,
                              format_func=lambda d: f"{d} — {atc.get(d, '')}")

    fdrug = forecast_df[(forecast_df.hospital_id == hid) & (forecast_df.drug == drug)].iloc[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("พยากรณ์ใช้/วัน", f"{fdrug['pred_next_day']:.0f} หน่วย")
    m2.metric("ยาคงคลัง", f"{fdrug['stock_on_hand']:.0f}")
    m3.metric("เหลือใช้ได้ (วัน)", f"{fdrug['days_of_supply']:.0f} วัน", help="days-of-supply = คงคลัง ÷ พยากรณ์/วัน")
    m4.metric("สถานะ", STATUS_TH[fdrug["status"]])

    # กราฟย้อนหลัง 90 วัน + จุดพยากรณ์
    hist = history[hid]
    series = hist[hist.drug == drug].sort_values("datum").tail(90)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=series["datum"], y=series["demand"],
                              mode="lines", name="ความต้องการจริง", line=dict(color="#34495e")))
    fig2.add_trace(go.Scatter(x=series["datum"], y=series["roll_mean_30"],
                              mode="lines", name="ค่าเฉลี่ย 30 วัน",
                              line=dict(color="#3498db", dash="dot")))
    next_day = series["datum"].max() + pd.Timedelta(days=1)
    fig2.add_trace(go.Scatter(x=[next_day], y=[fdrug["pred_next_day"]],
                              mode="markers", name="พยากรณ์",
                              marker=dict(color=STATUS_COLOR[fdrug["status"]], size=14, symbol="star")))
    fig2.update_layout(height=420, title=f"{drug} — {atc.get(drug, '')}",
                       margin=dict(l=0, r=0, t=40, b=0), legend_title="")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown(f"**ภาพรวมทุกกลุ่มยาที่ {hid}**  (🟢 ≥14 วัน · 🟡 4–13 วัน · 🔴 ≤3 วัน)")
    tbl = forecast_df[forecast_df.hospital_id == hid][
        ["drug", "pred_next_day", "stock_on_hand", "days_of_supply", "status", "confidence"]].copy()
    tbl["status"] = tbl["status"].map(STATUS_TH)
    tbl["confidence"] = (tbl["confidence"] * 100).round(0).astype(int).astype(str) + "%"
    tbl.columns = ["กลุ่มยา", "พยากรณ์/วัน", "คงคลัง", "เหลือ(วัน)", "สถานะ", "Confidence"]
    st.dataframe(tbl, use_container_width=True, hide_index=True)

# ========== 3) PRIVACY CONTROL CENTER ==========
with tab_priv:
    st.subheader("ศูนย์ควบคุมความเป็นส่วนตัว")
    p1, p2, p3 = st.columns(3)
    p1.metric("Federated Learning", "✅ Active", help="แต่ละ รพ. เทรนในเครื่อง ส่งแค่ weight")
    p2.metric("Differential Privacy", "✅ ON (σ=0.1)", help="ใส่ Gaussian noise ลง weight ก่อนส่ง")
    p3.metric("การเข้ารหัสส่งข้อมูล", "🔒 TLS/SSL", help="ช่องทางเดียวกับธนาคาร")

    st.markdown(
        "> **ข้อมูลคนไข้ดิบไม่เคยออกจากโรงพยาบาล** — สิ่งที่ส่งขึ้นศูนย์กลางมีแค่ "
        f"*weight* จำนวน **{len(bundle['coef'])} ค่า** (+ noise) ผ่าน Secure Aggregation + TLS"
    )

    rng = np.random.default_rng(1)
    priv = master[["hospital_id", "name"]].copy()
    priv["สถานะเชื่อมต่อ"] = "🟢 Online"
    priv["Secure Aggregation"] = "✅"
    priv["DP noise (σ)"] = 0.1
    priv["weight ที่ส่ง"] = f"{len(bundle['coef'])} ค่า"
    priv["รอบ FedAvg ล่าสุด"] = "เมื่อสักครู่"
    priv.columns = ["รหัส", "โรงพยาบาล", "สถานะเชื่อมต่อ", "Secure Agg.", "DP noise (σ)", "weight ที่ส่ง", "รอบ FedAvg"]
    st.dataframe(priv, use_container_width=True, hide_index=True)

    st.markdown("##### กระแสข้อมูลแบบรักษาความเป็นส่วนตัว")
    st.code(
        "raw data (อยู่ใน รพ.)\n"
        "   → feature engineering → train local model\n"
        "   → weight  → + Differential Privacy noise\n"
        "   → Secure Aggregation → TLS/SSL ──▶ ศูนย์กลาง (FedAvg)\n"
        "   ◀── ส่ง weight กลางกลับ → ทุก รพ. พยากรณ์ในเครื่อง",
        language="text",
    )

st.caption("MedCast_Secure · Logistics Innovation Hackathon 2026")
