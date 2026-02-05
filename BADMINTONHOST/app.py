import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Badminton Rolling Host", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #00ffcc !important; color: black !important; }
    h1, h2, h3 { color: #00ffcc !important; }
    div[data-testid="stExpander"] { background-color: #161b22 !important; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = "badminton_pro_rolling.json"
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


def arrange_court(court_name, locked_names=None):
    # Lấy danh sách những người Sẵn sàng và Đang không đánh ở sân khác
    busy_players = []
    for c, match in st.session_state.current_matches.items():
        if c != court_name and match:
            busy_players.extend([p['name'] for team in match for p in team])

    pool = [p for p in st.session_state.players if p['status'] == "Sẵn sàng" and p['name'] not in busy_players]
    pool = sorted(pool, key=lambda x: (x['sets'], -x['wait']))

    if len(pool) < 4:
        st.warning(f"Không đủ người để xếp trận cho {court_name}!")
        return None

    final_4 = []
    if locked_names and len(locked_names) == 2:
        final_4.extend([p for p in pool if p['name'] in locked_names])
        others = [p for p in pool if p['name'] not in locked_names]
        final_4.extend(others[:(4 - len(final_4))])
    else:
        final_4 = pool[:4]

    if len(final_4) < 4: return None

    p = sorted(final_4, key=lambda x: x['score'], reverse=True)
    #chia cặp cân bằng
    if locked_names and len(locked_names) == 2:
        t1 = [x for x in final_4 if x['name'] in locked_names]
        t2 = [x for x in final_4 if x['name'] not in locked_names]
    else:
        t1, t2 = [p[0], p[3]], [p[1], p[2]]

    return [t1, t2]

with st.sidebar:
    st.header("🏸 THÀNH VIÊN")
    with st.form("add_player", clear_on_submit=True):
        name = st.text_input("Tên khách")
        c1, c2 = st.columns(2)
        gen = c1.selectbox("Phái", ["Nam", "Nữ"])
        lvl = c2.selectbox("Trình", list(LEVEL_MAP.keys()))
        if st.form_submit_button("THÊM"):
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

st.title("🏸 ĐIỀU PHỐI CUỐN CHIẾU")
col_l, col_r = st.columns([2, 1.5])

with col_l:
    for court in ["Sân 3", "Sân 4"]:
        with st.container():
            st.subheader(f"🏟️ {court}")
            current = st.session_state.current_matches.get(court)

            if not current:
                #nếu sân trống, hiện nút lập trận
                ready_names = [p['name'] for p in st.session_state.players if p['status'] == "Sẵn sàng"]
                locked = st.multiselect(f"Ghép cặp (Sân {court}):", options=ready_names, max_selections=2,
                                        key=f"lock_{court}")
                if st.button(f"🚀 LẬP TRẬN {court.upper()}", key=f"btn_{court}"):
                    new_match = arrange_court(court, locked)
                    if new_match:
                        st.session_state.current_matches[court] = new_match
                        save_all();
                        st.rerun()
            else:
                #nếu đang có trận, hiện thông tin và nút Xong
                t1, t2 = current
                c1, cvs, c2 = st.columns([2, 0.5, 2])
                c1.write(f"**{t1[0]['name']} & {t1[1]['name']}**")
                cvs.write("vs")
                c2.write(f"**{t2[0]['name']} & {t2[1]['name']}**")

                if st.button(f"✅ XÁC NHẬN XONG {court.upper()}", key=f"done_{court}"):
                    played_names = [p['name'] for team in current for p in team]
                    #cập nhật lịch sử và số set
                    for team in current:
                        pair = tuple(sorted((team[0]['name'], team[1]['name'])))
                        st.session_state.pairing_history[pair] = st.session_state.pairing_history.get(pair, 0) + 1

                    for p in st.session_state.players:
                        if p['name'] in played_names:
                            p['sets'] += 1;
                            p['wait'] = 0
                        elif p['status'] == "Sẵn sàng":
                            p['wait'] += 1
                        if p['status'] == "Tạm nghỉ 1 set":
                            p['status'] = "Sẵn sàng"

                    st.session_state.current_matches[court] = None
                    save_all();
                    st.rerun()
            st.divider()

with col_r:
    st.subheader("📊 TRẠNG THÁI")
    if st.session_state.players:
        df_p = pd.DataFrame(st.session_state.players)
        st.bar_chart(df_p.set_index('name')['sets'])
        for i, p in enumerate(st.session_state.players):
            c_n, c_l, c_s = st.columns([1, 0.7, 1.2])
            wait_mark = "🔴" if p['wait'] >= 2 and p['status'] == "Sẵn sàng" else ""
            c_n.write(f"{wait_mark}**{p['name']}** ({p['sets']}s)")
            new_lvl = c_l.selectbox("Trình", list(LEVEL_MAP.keys()), index=list(LEVEL_MAP.keys()).index(p['level']),
                                    key=f"lvl_{i}")
            if new_lvl != p['level']: p['level'] = new_lvl; p['score'] = LEVEL_MAP[new_lvl]; save_all(); st.rerun()
            new_s = c_s.selectbox("Status", ["Sẵn sàng", "Tạm nghỉ 1 set", "Về sớm"],
                                  index=["Sẵn sàng", "Tạm nghỉ 1 set", "Về sớm"].index(p['status']), key=f"st_{i}")
            if new_s != p['status']: p['status'] = new_s; save_all(); st.rerun()