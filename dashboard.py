# Dashboard.py  
import streamlit as st
from sqlalchemy import create_engine, text
from pathlib import Path

st.set_page_config(page_title="US-14 — View Dashboard", layout="centered")
st.title("US-14 — View Dashboard")

# —— 1)  DB
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "habits.db"
DB_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DB_URL, future=True)

def init_db():
    # —— 2) begin() -> auto commit
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS habits(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            completion INTEGER NOT NULL DEFAULT 0
        )
        """))
        count = conn.execute(text("SELECT COUNT(*) FROM habits")).scalar()
        if count == 0:
            conn.execute(text("""
              INSERT INTO habits(name, active, completion) VALUES
              ('Drink water', 1, 40),
              ('Read 30 mins', 1, 70),
              ('Run 3km', 0, 0)
            """))

# —— 3) search without cache
def list_active():
    with engine.begin() as conn:
        return conn.execute(text(
            "SELECT id,name,completion FROM habits WHERE active=1 ORDER BY id"
        )).mappings().all()

def add_habit(name: str):
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO habits(name, active, completion) VALUES(:n, 1, 0)"
        ), {"n": name})

def update_completion(hid: int, val: int):
    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE habits SET completion=:v WHERE id=:i"
        ), {"v": int(val), "i": int(hid)})

init_db()
st.caption(f"DB path: {DB_PATH.resolve()}")  

# 新增
with st.expander("➕ Add Habit"):
    name = st.text_input("Habit name")
    if st.button("Add", disabled=not name):
        add_habit(name.strip())
        st.success("Added")
        st.rerun()  # ← run immediately after write

# list
st.subheader("Active Habits (auto refresh on save)")
rows = list_active()
if not rows:
    st.info("No active habits.")
else:
    for r in rows:
        col1, col2 = st.columns([3, 3], vertical_alignment="center")
        with col1:
            st.write(f"**{r['name']}** — {r['completion']}%")
            st.progress(int(r["completion"]))
        with col2:
            new_val = st.slider(
                f"Completion — {r['name']}",
                0, 100, int(r['completion']),
                key=f"comp-{r['id']}"
            )
            if st.button("Save", key=f"save-{r['id']}"):
                update_completion(r['id'], new_val)
                st.success("Saved")
                st.rerun()  # refresh immediately

# refresh button
if st.button("🔄 Refresh"):
    st.rerun()