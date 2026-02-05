import streamlit as st
import pandas as pd
import json
import os
import itertools

# 1. CẤU HÌNH GIAO DIỆN
st.set_page_config(page_title="Badminton Pro - Social Edition", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    h1, h2, h3 { color: #00ffcc !important; text-align: center; }
    .stadium-container {
        background-color: #2d5a27; border: 4px solid #ffffff; border-radius: 5px;
        position: relative; width: 100%; height: 320px; margin: 10px 0;
        display: flex; flex-direction: column; justify-content: space-around; align-items: center;
    }
    .net-line { width: 100%; border-top: 3px dashed #ffffff; position: absolute; top: 50%; }
    .team-box { background-color: rgba(0, 0, 0, 0.7); padding: 10px; border-radius: 10px; border: 2px solid #00ffcc; width: 85%; text-align: center; z-index: 1; }
    .player-name { color: #ffffff; font-weight: bold; font-size: 1.1rem; }
    .vs-badge { background-color: #ff3366; color: white; padding: 2px 12px; border-radius: 20px; font-weight: bold; z-index: 2; }
    .stButton>button { border-radius: 20px; font-weight: bold; background: linear-gradient(45deg, #00ffcc, #0099ff) !important; color: #000 !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. HỆ THỐNG DỮ LIỆU
DB_FILE = "badminton_social_data.json"
LEVEL_MAP = {'Yếu': 1, 'TBY': 2, 'TB-': 3, 'TB': 4}


def save_all():
    data = {
        "players": st.session_state.players,
        "encounter_history": st.session_state.encounter_history,
        "matches": st.session_state.current_matches
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if 'players' not in st.session_state:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            st.session_state.players = d.get("players", [])
            st.session_state.encounter_history = d.get("encounter_history", {})
            st.session_state.current_matches = d.get("matches", {"Sân 3": None, "Sân 4": None})
    else:
        st.session_state.players, st.session_state.encounter_history = [], {}
        st.session_state.current_matches = {"Sân 3": None, "Sân 4": None}


# --- THUẬT TOÁN XẾP TRẬN ƯU TIÊN NGƯỜI LẠ ---
def arrange_court_social(court_name, locked_names=None):
    busy_players = []
    for c, match in st.session_state.current_matches.items():
        if c != court_name and match:
            busy_players.extend([p['name'] for team in match for p in team])

    # Lấy pool người sẵn sàng
    pool = [p for p in st.session_state.players if p['status'] == "Sẵn sàng" and p['name'] not in busy_players]
    pool = sorted(pool, key=lambda x: (x['sets'], -x['wait']))

    if len(pool) < 4: return None

    # Chọn ra 4 người (ưu tiên locked hoặc người đợi lâu)
    candidates = []
    if locked_names and len(locked_names) == 2:
        candidates.extend([p for p in pool if p['name'] in locked_names])
        others = [p for p in pool if p['name'] not in locked_names]
        candidates.extend(others[:(4 - len(candidates))])
    else:
        candidates = pool[:4]

    # Thử tất cả các cách chia 2-2 để tìm cách ít lặp lại nhất
    best_match = None
    min_penalty = float('inf')

    # Tạo tất cả tổ hợp 2 người từ 4 người
    for combo in itertools.combinations(candidates, 2):
        t1 = list(combo)
        t2 = [p for p in candidates if p not in t1]

        # Tính điểm phạt dựa trên lịch sử gặp nhau
        penalty = 0
        names_4 = [p['name'] for p in candidates]

        # Phạt nếu cùng team đã từng gặp
        p1, p2 = t1[0]['name'], t1[1]['name']
        penalty += st.session_state.encounter_history.get(p1, {}).get(p2, 0) * 10

        p3, p4 = t2[0]['name'], t2[1]['name']
        penalty += st.session_state.encounter_history.get(p3, {}).get(p4, 0) * 10

        # Phạt chênh lệch trình độ
        diff = abs((t1[0]['score'] + t1[1]['score']) - (t2[0]['score'] + t2[1]['score']))
        penalty += diff * 2

        if penalty < min_penalty:
            min_penalty = penalty
            best_match = [t1, t2]

    return best_match


# --- SIDEBAR & MAIN ---
with st.sidebar:
    st.header("🏸 QUẢN LÝ")
    with st.form("add_p", clear_on_submit=True):
        n = st.text_input("Tên");
        c_g, c_l = st.columns(2)
        g = c_g.selectbox("Phái", ["Nam", "Nữ"]);
        l = c_l.selectbox("Trình", list(LEVEL_MAP.keys()))
        if st.form_submit_button("THÊM"):
            if n: st.session_state.players.append(
                {"name": n, "gender": g, "level": l, "score": LEVEL_MAP[l], "sets": 0, "wait": 0,
                 "status": "Sẵn sàng"}); save_all(); st.rerun()

st.write("### 🏸 ĐIỀU PHỐI GIAO LƯU (ƯU TIÊN GẶP NGƯỜI LẠ)")
col_c, col_s = st.columns([2.2, 1.8])

with col_c:
    for court in ["Sân 3", "Sân 4"]:
        match = st.session_state.current_matches.get(court)
        st.markdown(f"#### 🏟️ {court}")
        if not match:
            ready = [p['name'] for p in st.session_state.players if p['status'] == "Sẵn sàng"]
            locked = st.multiselect(f"Ghép cặp cho {court}:", options=ready, max_selections=2, key=f"lk_{court}")
            if st.button(f"LẬP TRẬN {court.upper()}", key=f"b_{court}", use_container_width=True):
                new_m = arrange_court_social(court, locked)
                if new_m: st.session_state.current_matches[court] = new_m; save_all(); st.rerun()
        else:
            t1, t2 = match
            st.markdown(
                f'<div class="stadium-container"><div class="net-line"></div><div class="team-box"><div class="player-name">{t1[0]["name"]} & {t1[1]["name"]}</div></div><div class="vs-badge">VS</div><div class="team-box"><div class="player-name">{t2[0]["name"]} & {t2[1]["name"]}</div></div></div>',
                unsafe_allow_html=True)
            if st.button(f"HOÀN THÀNH {court.upper()} ✅", key=f"d_{court}", use_container_width=True):
                all_n = [p['name'] for team in match for p in team]
                # Lưu lịch sử gặp nhau (Penalty)
                for p1, p2 in itertools.combinations(all_n, 2):
                    for p in [p1, p2]:
                        if p not in st.session_state.encounter_history: st.session_state.encounter_history[p] = {}
                    st.session_state.encounter_history[p1][p2] = st.session_state.encounter_history[p1].get(p2, 0) + 1
                    st.session_state.encounter_history[p2][p1] = st.session_state.encounter_history[p2].get(p1, 0) + 1

                for p in st.session_state.players:
                    if p['name'] in all_n:
                        p['sets'] += 1; p['wait'] = 0
                    elif p['status'] == "Sẵn sàng":
                        p['wait'] += 1
                    if p['status'] == "Tạm nghỉ 1 set": p['status'] = "Sẵn sàng"
                st.session_state.current_matches[court] = None;
                save_all();
                st.rerun()

with col_s:
    st.markdown("#### 📊 THỐNG KÊ")
    if st.session_state.players:
        df = pd.DataFrame(st.session_state.players)
        st.bar_chart(df.set_index('name')['sets'])
        for i, p in enumerate(st.session_state.players):
            with st.expander(f"{p['name']} ({p['sets']}s) - {p['level']}"):
                c1, c2 = st.columns(2)
                p['level'] = c1.selectbox("Trình", list(LEVEL_MAP.keys()),
                                          index=list(LEVEL_MAP.keys()).index(p['level']), key=f"lv_{i}")
                p['score'] = LEVEL_MAP[p['level']]
                p['status'] = c2.selectbox("Trạng thái", ["Sẵn sàng", "Tạm nghỉ 1 set", "Về sớm"],
                                           index=["Sẵn sàng", "Tạm nghỉ 1 set", "Về sớm"].index(p['status']),
                                           key=f"ss_{i}")
                if st.button("Lưu", key=f"v_{i}"): save_all(); st.rerun()