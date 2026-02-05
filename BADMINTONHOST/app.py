import streamlit as st
import pandas as pd
import json
import os

# 1. CẤU HÌNH GIAO DIỆN & VẼ SÂN CẦU LÔNG BẰNG CSS
st.set_page_config(page_title="Badminton Stadium Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    h1, h2, h3 { color: #00ffcc !important; text-align: center; }

    /* Khung sân cầu lông */
    .stadium-container {
        background-color: #2d5a27;
        border: 4px solid #ffffff;
        border-radius: 5px;
        position: relative;
        width: 100%;
        height: 320px;
        margin: 10px 0;
        display: flex;
        flex-direction: column;
        justify-content: space-around;
        align-items: center;
        box-shadow: 0 0 20px rgba(0,255,204,0.2);
    }

    /* Vạch kẻ sân */
    .court-line {
        position: absolute;
        border: 1px solid rgba(255,255,255,0.5);
        pointer-events: none;
    }
    .net-line {
        width: 100%;
        border-top: 3px dashed #ffffff;
        position: absolute;
        top: 50%;
    }

    /* Vị trí Team */
    .team-box {
        background-color: rgba(0, 0, 0, 0.6);
        padding: 10px;
        border-radius: 10px;
        border: 2px solid #00ffcc;
        width: 80%;
        text-align: center;
        z-index: 1;
    }
    .player-name {
        color: #ffffff;
        font-weight: bold;
        font-size: 1.1rem;
        margin: 2px 0;
    }
    .vs-badge {
        background-color: #ff3366;
        color: white;
        padding: 2px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
        z-index: 2;
    }

    /* Nút bấm Neon */
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
        background: linear-gradient(45deg, #00ffcc, #0099ff) !important;
        color: #000 !important;
        border: none !important;
        transition: 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 15px #00ffcc;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. HỆ THỐNG DỮ LIỆU
DB_FILE = "badminton_stadium_data.json"
LEVEL_MAP = {'Yếu': 1, 'TBY': 2, 'TB-': 3, 'TB': 4}


def save_all():
    data = {
        "players": st.session_state.players,
        "history": {str(k): v for k, v in st.session_state.pairing_history.items()},
        "matches": st.session_state.current_matches
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if 'players' not in st.session_state:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            st.session_state.players = d.get("players", [])
            st.session_state.pairing_history = {tuple(eval(k)): v for k, v in d.get("history", {}).items()}
            st.session_state.current_matches = d.get("matches", {"Sân 3": None, "Sân 4": None})
    else:
        st.session_state.players, st.session_state.pairing_history = [], {}
        st.session_state.current_matches = {"Sân 3": None, "Sân 4": None}


# --- LOGIC XẾP TRẬN ---
def arrange_court(court_name, locked_names=None):
    busy_players = []
    for c, match in st.session_state.current_matches.items():
        if c != court_name and match:
            busy_players.extend([p['name'] for team in match for p in team])

    pool = [p for p in st.session_state.players if p['status'] == "Sẵn sàng" and p['name'] not in busy_players]
    pool = sorted(pool, key=lambda x: (x['sets'], -x['wait']))

    if len(pool) < 4: return None

    final_4 = []
    if locked_names and len(locked_names) == 2:
        final_4.extend([p for p in pool if p['name'] in locked_names])
        others = [p for p in pool if p['name'] not in locked_names]
        final_4.extend(others[:(4 - len(final_4))])
    else:
        final_4 = pool[:4]

    if len(final_4) < 4: return None
    p = sorted(final_4, key=lambda x: x['score'], reverse=True)

    if locked_names and len(locked_names) == 2:
        t1 = [x for x in final_4 if x['name'] in locked_names]
        t2 = [x for x in final_4 if x['name'] not in locked_names]
    else:
        t1, t2 = [p[0], p[3]], [p[1], p[2]]
    return [t1, t2]


# --- SIDEBAR ---
with st.sidebar:
    st.header("🏸 QUẢN LÝ KHÁCH")
    with st.form("add_player", clear_on_submit=True):
        name = st.text_input("Tên khách hàng")
        c1, c2 = st.columns(2)
        gen = c1.selectbox("Phái", ["Nam", "Nữ"])
        lvl = c2.selectbox("Trình", list(LEVEL_MAP.keys()))
        if st.form_submit_button("THÊM VÀO SÂN"):
            if name:
                st.session_state.players.append(
                    {"name": name, "gender": gen, "level": lvl, "score": LEVEL_MAP[lvl], "sets": 0, "wait": 0,
                     "status": "Sẵn sàng"})
                save_all();
                st.rerun()
    if st.button("🔴 RESET BUỔI MỚI"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.session_state.clear();
        st.rerun()

# --- GIAO DIỆN CHÍNH ---
st.write("### 🏸 HỆ THỐNG ĐIỀU PHỐI SÂN VẬN ĐỘNG")
col_courts, col_stats = st.columns([2.2, 1.8])

with col_courts:
    for court in ["Sân 3", "Sân 4"]:
        match = st.session_state.current_matches.get(court)
        st.markdown(f"#### 🏟️ {court}")

        if not match:
            # Giao diện khi sân trống
            ready_names = [p['name'] for p in st.session_state.players if p['status'] == "Sẵn sàng"]
            locked = st.multiselect(f"Ghép cặp yêu cầu cho {court}:", options=ready_names, max_selections=2,
                                    key=f"lk_{court}")
            if st.button(f"LẬP TRẬN {court.upper()}", key=f"btn_{court}", use_container_width=True):
                new_m = arrange_court(court, locked)
                if new_m:
                    st.session_state.current_matches[court] = new_m
                    save_all();
                    st.rerun()
        else:
            # VẼ SÂN CẦU LÔNG
            t1, t2 = match
            st.markdown(f"""
                <div class="stadium-container">
                    <div class="court-line" style="inset: 5px;"></div>
                    <div class="net-line"></div>
                    <div class="team-box">
                        <div class="player-name">{t1[0]['name']}</div>
                        <div class="player-name">{t1[1]['name']}</div>
                    </div>
                    <div class="vs-badge">VS</div>
                    <div class="team-box">
                        <div class="player-name">{t2[0]['name']}</div>
                        <div class="player-name">{t2[1]['name']}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if st.button(f"HOÀN THÀNH {court.upper()} ✅", key=f"done_{court}", use_container_width=True):
                p_names = [p['name'] for team in match for p in team]
                for team in match:
                    pair = tuple(sorted((team[0]['name'], team[1]['name'])))
                    st.session_state.pairing_history[pair] = st.session_state.pairing_history.get(pair, 0) + 1
                for p in st.session_state.players:
                    if p['name'] in p_names:
                        p['sets'] += 1; p['wait'] = 0
                    elif p['status'] == "Sẵn sàng":
                        p['wait'] += 1
                    if p['status'] == "Tạm nghỉ 1 set": p['status'] = "Sẵn sàng"
                st.session_state.current_matches[court] = None
                save_all();
                st.rerun()
        st.write("")

with col_stats:
    st.markdown("#### 📊 TRẠNG THÁI & CÔNG BẰNG")
    if st.session_state.players:
        df = pd.DataFrame(st.session_state.players)
        st.bar_chart(df.set_index('name')['sets'], color="#00ffcc")

        for i, p in enumerate(st.session_state.players):
            with st.expander(
                    f"{'🔴 ' if p['wait'] >= 2 and p['status'] == 'Sẵn sàng' else ''}{p['name']} ({p['sets']} set)"):
                c1, c2 = st.columns(2)
                p['level'] = c1.selectbox("Trình", list(LEVEL_MAP.keys()),
                                          index=list(LEVEL_MAP.keys()).index(p['level']), key=f"l_{i}")
                p['score'] = LEVEL_MAP[p['level']]
                p['status'] = c2.selectbox("Trạng thái", ["Sẵn sàng", "Tạm nghỉ 1 set", "Về sớm"],
                                           index=["Sẵn sàng", "Tạm nghỉ 1 set", "Về sớm"].index(p['status']),
                                           key=f"s_{i}")
                if st.button("Lưu thay đổi", key=f"sv_{i}"):
                    save_all();
                    st.rerun()