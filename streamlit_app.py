import streamlit as st
from datetime import datetime, date
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, select
import plotly.express as px

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
# CÁC HÀM TƯƠNG TÁC DATABASE
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
    with engine.begin() as conn:
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
    with engine.begin() as conn:
        meta = MetaData()
        meta.reflect(bind=engine)
        tasks = meta.tables["tasks"]
        upd = tasks.update().where(tasks.c.id == task_id).values(done=done)
        conn.execute(upd)

def delete_task(engine, task_id):
    with engine.begin() as conn:
        meta = MetaData()
        meta.reflect(bind=engine)
        tasks = meta.tables["tasks"]
        d = tasks.delete().where(tasks.c.id == task_id)
        conn.execute(d)

# ---------------------------
# GIAO DIỆN STREAMLIT
# ---------------------------
st.set_page_config(page_title="Task Tracker", layout="wide")
st.title("📋 Task Tracker — Theo dõi công việc cá nhân")

engine = get_engine()
init_db(engine)

# Tabs chính
tab1, tab2, tab3 = st.tabs(["📥 Nhập công việc", "📊 Theo dõi công việc", "📈 Dashboard"])

# ==============================
# TAB 1: NHẬP CÔNG VIỆC
# ==============================
with tab1:
    st.header("➕ Thêm công việc mới")
    with st.form("add_task_form", clear_on_submit=True):
        title = st.text_input("Tiêu đề công việc")
        detail = st.text_area("Chi tiết công việc")
        due = st.date_input("Ngày hoàn thành (tùy chọn)")
        priority = st.selectbox("Mức ưu tiên", [1, 2, 3], format_func=lambda x: {1: "Cao", 2: "Trung bình", 3: "Thấp"}[x])
        tags = st.text_input("Từ khóa (tags)")
        submitted = st.form_submit_button("Thêm công việc")
        if submitted:
            if title.strip():
                insert_task(engine, title, detail, due, priority, tags)
                st.success("✅ Đã thêm công việc!")
                st.rerun()
            else:
                st.warning("❗ Vui lòng nhập tiêu đề công việc.")

# ==============================
# TAB 2: THEO DÕI CÔNG VIỆC
# ==============================
with tab2:
    st.header("📋 Danh sách công việc")
    rows = fetch_all(engine)

    if not rows:
        st.info("Chưa có công việc nào.")
    else:
        df = pd.DataFrame(rows)
        df_display = df.copy()
        df_display["Trạng thái"] = df_display["done"].map({True: "✅ Hoàn thành", False: "🕓 Chưa xong"})
        df_display["Mức ưu tiên"] = df_display["priority"].map({1: "Cao", 2: "Trung bình", 3: "Thấp"})
        df_display = df_display.rename(columns={
            "title": "Tiêu đề",
            "detail": "Chi tiết",
            "due_date": "Hạn hoàn thành",
            "tags": "Tags"
        })[["id", "Tiêu đề", "Chi tiết", "Hạn hoàn thành", "Mức ưu tiên", "Tags", "Trạng thái"]]

        st.dataframe(df_display, use_container_width=True)

        # Tác vụ cập nhật
        selected_id = st.selectbox("Chọn ID công việc để cập nhật:", df_display["id"])
        action = st.radio("Hành động", ["Đánh dấu hoàn thành", "Xóa công việc"])
        if st.button("Thực hiện"):
            if action == "Đánh dấu hoàn thành":
                update_task_done(engine, int(selected_id), True)
                st.success("🎯 Đã đánh dấu hoàn thành!")
            else:
                delete_task(engine, int(selected_id))
                st.warning("🗑️ Đã xóa công việc!")
            st.rerun()

# ==============================
# TAB 3: DASHBOARD
# ==============================
with tab3:
    st.header("📈 Thống kê công việc")

    rows = fetch_all(engine)
    if not rows:
        st.info("Chưa có dữ liệu thống kê.")
    else:
        df = pd.DataFrame(rows)

        col1, col2, col3 = st.columns(3)
        total_tasks = len(df)
        done_tasks = df["done"].sum()
        undone_tasks = total_tasks - done_tasks
        col1.metric("Tổng số công việc", total_tasks)
        col2.metric("Đã hoàn thành", done_tasks)
        col3.metric("Chưa hoàn thành", undone_tasks)

        st.divider()
        # Biểu đồ trạng thái
        fig1 = px.pie(df, names="done", title="Tỷ lệ hoàn thành", color="done",
                      color_discrete_map={True: "green", False: "red"},
                      labels={"done": "Trạng thái"})
        fig1.update_traces(textinfo="percent+label")
        st.plotly_chart(fig1, use_container_width=True)

        # Biểu đồ theo mức ưu tiên
        fig2 = px.histogram(df, x="priority", color="done",
                            barmode="group", title="Số lượng công việc theo mức ưu tiên",
                            labels={"priority": "Mức ưu tiên", "count": "Số lượng"})
        st.plotly_chart(fig2, use_container_width=True)
