# streamlit_app.py
# Task Tracker App (Streamlit + SQLite)
# Phiên bản hoàn chỉnh 2025 — fix SQLAlchemy 2.0, st.rerun() và auto commit DB

import streamlit as st
from datetime import datetime, date
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, select

# ---------------------------
# CẤU HÌNH DATABASE
# ---------------------------
DB_FILENAME = "tasks.db"
DB_URL = f"sqlite:///{DB_FILENAME}"

def get_engine():
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
    return engine

def init_db(engine):
    meta = MetaData()
    tasks = Table(
        "tasks", meta,
        Column("id", Integer, primary_key=True),
        Column("title", String, nullable=False),
        Column("detail", String),
        Column("created_at", String, nullable=False),
        Column("due_date", String),
        Column("priority", Integer, nullable=False, default=2),
        Column("tags", String),
        Column("done", Boolean, nullable=False, default=False)
    )
    meta.create_all(engine)

# ---------------------------
# CÁC HÀM TƯƠNG TÁC DATABASE (ĐÃ THÊM COMMIT)
# ---------------------------
def fetch_all(engine):
    with engine.connect() as conn:
        meta = MetaData()
        meta.reflect(bind=engine)
        tasks = meta.tables["tasks"]
        stmt = select(tasks).order_by(tasks.c.done, tasks.c.priority, tasks.c.due_date.nulls_last())
        result = conn.execute(stmt).fetchall()
        return [dict(row._mapping) for row in result]

def insert_task(engine, title, detail, due_date, priority, tags):
    with engine.begin() as conn:  # ✅ auto commit
        meta = MetaData()
        meta.reflect(bind=engine)
        tasks = meta.tables["tasks"]
        ins = tasks.insert().values(
            title=title,
            detail=detail,
            created_at=datetime.utcnow().isoformat(),
            due_date=due_date.isoformat() if due_date else None,
            priority=priority,
            tags=tags,
            done=False
        )
        conn.execute(ins)

def update_task_done(engine, task_id, done):
    with engine.begin() as conn:  # ✅ auto commit
        meta = MetaData()
        meta.reflect(bind=engine)
        tasks = meta.tables["tasks"]
        upd = tasks.update().where(tasks.c.id == task_id).values(done=done)
        conn.execute(upd)

def delete_task(engine, task_id):
    with engine.begin() as conn:  # ✅ auto commit
        meta = MetaData()
        meta.reflect(bind=engine)
        tasks = meta.tables["tasks"]
        d = tasks.delete().where(tasks.c.id == task_id)
        conn.execute(d)

# ---------------------------
# GIAO DIỆN STREAMLIT
# ---------------------------
st.set_page_config(page_title="Task Tracker", layout="centered")
st.title("📋 Task Tracker — Theo dõi công việc cá nhân")

engine = get_engine()
init_db(engine)

# ---- Form thêm công việc mới ----
st.sidebar.header("➕ Thêm công việc mới")
with st.sidebar.form("add_task_form", clear_on_submit=True):
    title = st.text_input("Tiêu đề công việc")
    detail = st.text_area("Chi tiết")
    due = st.date_input("Ngày hoàn thành (tùy chọn)")
    priority = st.selectbox("Mức ưu tiên", [1, 2, 3], format_func=lambda x: {1: "Cao", 2: "Trung bình", 3: "Thấp"}[x])
    tags = st.text_input("Từ khóa (tags)")
    submitted = st.form_submit_button("Thêm")
    if submitted:
        if title.strip():
            insert_task(engine, title, detail, due, priority, tags)
            st.success("✅ Đã thêm công việc!")
            st.rerun()  # ✅ cập nhật danh sách ngay
        else:
            st.warning("❗ Vui lòng nhập tiêu đề công việc.")

# ---- Hiển thị danh sách ----
st.subheader("📋 Danh sách công việc")

rows = fetch_all(engine)
if not rows:
    st.info("Chưa có công việc nào.")
else:
    df = pd.DataFrame(rows)
    for _, row in df.iterrows():
        c1, c2 = st.columns([0.1, 0.9])
        with c1:
            checked = st.checkbox("", value=row["done"], key=row["id"])
            if checked != row["done"]:
                update_task_done(engine, row["id"], checked)
                st.rerun()
        with c2:
            st.write(f"**{row['title']}**")
            st.caption(f"Ưu tiên: {row['priority']} | Hạn: {row['due_date']} | Tags: {row['tags']}")
            if row["detail"]:
                st.write(row["detail"])
            if st.button("🗑️ Xóa", key=f"del_{row['id']}"):
                delete_task(engine, row["id"])
                st.rerun()

# ---- Xuất file CSV ----
st.subheader("📦 Xuất dữ liệu")
if st.button("Tải danh sách CSV"):
    df = pd.DataFrame(fetch_all(engine))
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Tải xuống", csv, "tasks.csv", "text/csv")
