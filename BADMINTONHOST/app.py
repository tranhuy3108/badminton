import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Badminton Pro Host", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #00ffcc !important; color: black !important; }
    h1, h2, h3 { color: #00ffcc !important; font-family: 'Segoe UI', sans-serif; }
    div[data-testid="stExpander"] { background-color: #161b22 !important; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = "badminton_pro_v4.json"


def save_all():
    data = {
        "players": st.session_state.players,
        "round": st.session_state.round_number,
        "history": {str(k): v for k, v in st.session_state.pairing_history.items()}
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if 'players' not in st.session_state:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            st.session_state.players = d.get("players", [])
            st.session_state.round_number = d.get("round", 1)
            st.session_state.pairing_history = {tuple(eval(k)): v for k, v in d.get("history", {}).items()}
    else:
        st.session_state.players, st.session_state.round_number, st.session_state.pairing_history = [], 1, {}

# --- SIDEBAR ---
with st.sidebar:
    st.header("🏸 THÀNH VIÊN")
    with st.form("add_player", clear_on_submit=True):
        name = st.text_input("Tên khách")
        c1, c2 = st.columns(2)
        gen = c1.selectbox("Phái", ["Nam", "Nữ"])
        lvl = c2.selectbox("Trình", ["Yếu", "TBY", "TB-", "TB"])
        if st.form_submit_button("THÊM"):
            if name:
                st.session_state.players.append({
                    "name": name, "gender": gen, "level": lvl,
                    "score": {'Yếu': 1, 'TBY': 2, 'TB-': 3, 'TB': 4}[lvl],
                    "sets": 0, "wait": 0, "status": "Sẵn sàng"
                })
                save_all();
                st.rerun()

    st.markdown("---")
    if st.button("🔴 RESET BUỔI MỚI"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.session_state.clear();
        st.rerun()

# --- GIAO DIỆN CHÍNH ---
st.title(f"🏟️ ĐIỀU PHỐI VÒNG {st.session_state.round_number}")
col_left, col_right = st.columns([2, 1.4])

with col_left:
    # Ghép cặp yêu cầu
    ready_names = [p['name'] for p in st.session_state.players if p['status'] == "Sẵn sàng"]
    locked = st.multiselect("🤝 Ghép cặp yêu cầu (Sân 3):", options=ready_names, max_selections=2)

    if st.button("🚀 LẬP TRẬN ĐẤU MỚI", type="primary"):
        ready_pool = sorted([p for p in st.session_state.players if p['status'] == "Sẵn sàng"],
                            key=lambda x: (x['sets'], -x['wait']))

        if len(ready_pool) < 4:
            st.error("Không đủ người sẵn sàng!")
        else:
            final_8 = []
            if len(locked) == 2:
                final_8.extend([p for p in ready_pool if p['name'] in locked])
                others = [p for p in ready_pool if p['name'] not in locked]
                final_8.extend(others[:6])
            else:
                final_8 = ready_pool[:8]


            def split_team(p_list, lock=None):
                if len(p_list) < 4: return None
                p = sorted(p_list, key=lambda x: x['score'], reverse=True)
                if lock:
                    t1 = [x for x in p_list if x['name'] in lock]
                    t2 = [x for x in p_list if x['name'] not in lock]
                else:
                    t1, t2 = [p[0], p[3]], [p[1], p[2]]
                return t1, t2


            m = {"Sân 3": split_team(final_8[:4], locked if len(locked) == 2 else None)}
            m["Sân 4"] = split_team(final_8[4:]) if len(final_8) >= 8 else None

            st.session_state.current_matches = m
            st.session_state.s3_done = False
            st.session_state.s4_done = (m["Sân 4"] is None)

    # Hiển thị trận đấu
    if st.session_state.get('current_matches'):
        for court, teams in st.session_state.current_matches.items():
            if teams:
                with st.expander(f"🏟️ {court}", expanded=True):
                    t1, t2 = teams
                    c1, cvs, c2 = st.columns([2, 0.5, 2])
                    c1.markdown(f"**{t1[0]['name']} & {t1[1]['name']}**")
                    cvs.markdown("<h3 style='text-align:center;'>VS</h3>", unsafe_allow_html=True)
                    c2.markdown(f"**{t2[0]['name']} & {t2[1]['name']}**")
                    if st.checkbox(f"Xong {court}", key=f"v_{court}"):
                        if court == "Sân 3":
                            st.session_state.s3_done = True
                        else:
                            st.session_state.s4_done = True

        if st.session_state.s3_done and st.session_state.s4_done:
            if st.button("XÁC NHẬN HOÀN THÀNH ✅"):
                played = []
                for ct in st.session_state.current_matches.values():
                    if ct:
                        for team in ct:
                            p1, p2 = team[0]['name'], team[1]['name']
                            st.session_state.pairing_history[
                                tuple(sorted((p1, p2)))] = st.session_state.pairing_history.get(tuple(sorted((p1, p2))),
                                                                                                0) + 1
                            played.extend([p1, p2])

                for p in st.session_state.players:
                    if p['name'] in played:
                        p['sets'] += 1;
                        p['wait'] = 0
                    elif p['status'] == "Sẵn sàng":
                        p['wait'] += 1
                    if p['status'] == "Tạm nghỉ 1 set":
                        p['status'] = "Sẵn sàng"

                st.session_state.round_number += 1
                st.session_state.current_matches = None
                save_all();
                st.rerun()

with col_right:
    st.subheader("📊 BIỂU ĐỒ SỐ SET")
    if st.session_state.players:
        df_p = pd.DataFrame(st.session_state.players)
        # Biểu đồ cột ngang cho dễ nhìn trên điện thoại
        st.bar_chart(df_p.set_index('name')['sets'])

        st.markdown("---")
        for i, p in enumerate(st.session_state.players):
            c_n, c_s = st.columns([1, 1.3])
            wait_mark = "🔴" if p['wait'] >= 2 and p['status'] == "Sẵn sàng" else "⚪"
            c_n.write(f"{wait_mark} **{p['name']}** ({p['sets']}s)")
            new_s = c_s.selectbox("Trạng thái", ["Sẵn sàng", "Tạm nghỉ 1 set", "Về sớm"],
                                  index=["Sẵn sàng", "Tạm nghỉ 1 set", "Về sớm"].index(p['status']), key=f"st_{i}")
            if new_s != p['status']:
                p['status'] = new_s;
                save_all();
                st.rerun()