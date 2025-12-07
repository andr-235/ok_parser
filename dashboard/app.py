import os
import sys
import logging
from logging.handlers import RotatingFileHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from pymongo import MongoClient

# Настройка логирования в файл
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "dashboard.log")

file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(file_formatter)

# Консольный handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(file_formatter)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, console_handler],
)

from dashboard.components.charts import (
    render_comments_by_date,
    render_top_authors,
    render_comments_heatmap,
)
from dashboard.components.filters import (
    render_group_filter,
    render_date_filter,
    render_author_filter,
    apply_filters,
)

st.set_page_config(
    page_title="OK Parser Dashboard",
    page_icon="📊",
    layout="wide",
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
MONGO_DB = os.getenv("MONGO_DB_NAME", "okdb")


@st.cache_resource
def get_mongo_client():
    return MongoClient(MONGO_URI)


@st.cache_data(ttl=60)
def load_comments() -> pd.DataFrame:
    client = get_mongo_client()
    db = client[MONGO_DB]
    comments = list(db.comments.find({}, {"_id": 0}))
    return pd.DataFrame(comments) if comments else pd.DataFrame()


@st.cache_data(ttl=60)
def load_groups() -> pd.DataFrame:
    client = get_mongo_client()
    db = client[MONGO_DB]
    groups = list(db.groups.find({}, {"_id": 0}))
    return pd.DataFrame(groups) if groups else pd.DataFrame()


def run_parser(group_id: str, max_discussions: int | None = None) -> dict:
    from parser.config import get_settings
    from parser.api import OKAuth, OKApiClient
    from parser.repositories import GroupRepository, CommentRepository, DiscussionRepository
    from parser.services import ParserService
    
    settings = get_settings()
    client = get_mongo_client()
    db = client[MONGO_DB]
    
    auth = OKAuth(
        client_id=settings.ok_client_id,
        client_secret=settings.ok_client_secret,
        access_token=settings.ok_access_token,
        public_key=settings.ok_public_key,
        session_key=settings.ok_session_key,
        session_secret_key=settings.ok_session_secret_key,
    )
    
    api = OKApiClient(
        auth=auth,
        base_url=settings.api_base_url,
        rate_limit_delay=settings.rate_limit_delay,
    )
    
    group_repo = GroupRepository(db)
    comment_repo = CommentRepository(db)
    discussion_repo = DiscussionRepository(db)
    
    service = ParserService(
        api=api,
        group_repo=group_repo,
        comment_repo=comment_repo,
        discussion_repo=discussion_repo,
    )
    
    return service.full_parse(group_id, max_discussions=max_discussions)


def render_parser_ui():
    st.subheader("🔄 Парсер")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        group_id = st.text_input(
            "Group ID",
            placeholder="Введите ID группы OK",
            help="ID группы из URL: ok.ru/group/XXXXXXXXXX",
            key="group_id_input",
        )
    
    with col2:
        max_disc = st.number_input(
            "Макс. обсуждений",
            min_value=1,
            max_value=100,
            value=10,
            help="Ограничение количества обсуждений для парсинга",
            key="max_disc_input",
        )
    
    if st.button("🚀 Запустить парсинг", type="primary", disabled=not group_id, key="parse_btn"):
        if group_id:
            with st.spinner(f"Парсинг группы {group_id}..."):
                try:
                    result = run_parser(group_id, max_discussions=max_disc)
                    st.success(
                        f"✅ Готово! Группа: {result['group']}, "
                        f"обсуждений: {result['discussions_parsed']}, "
                        f"комментариев: {result['comments_saved']}"
                    )
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    print(tb)  # В логи контейнера
                    st.error(f"❌ Ошибка: {e}")
                    st.code(tb)


def main():
    st.title("📊 OK Parser Dashboard")
    
    with st.sidebar:
        st.header("⚙️ Парсинг")
        render_parser_ui()
        st.divider()
        st.header("🔍 Фильтры")
    
    with st.spinner("Загрузка данных..."):
        df_comments = load_comments()
        df_groups = load_groups()
    
    if df_comments.empty:
        st.info("👆 Введите Group ID в боковой панели и нажмите 'Запустить парсинг'")
        
        st.markdown("""
        ### Как получить Group ID:
        1. Откройте группу в Одноклассниках
        2. URL будет вида: `ok.ru/group/XXXXXXXXXX`
        3. Скопируйте числовой ID (XXXXXXXXXX)
        """)
        return
    
    with st.sidebar:
        group_filter = render_group_filter(df_comments, df_groups)
        start_date, end_date = render_date_filter(df_comments)
        author_filter = render_author_filter(df_comments)
    
    filtered_df = apply_filters(
        df_comments,
        group_id=group_filter,
        start_date=start_date,
        end_date=end_date,
        author=author_filter,
    )
    
    if not df_groups.empty and "uid" in df_groups.columns and "name" in df_groups.columns:
        groups_dict = dict(zip(df_groups["uid"], df_groups["name"]))
        filtered_df = filtered_df.copy()
        filtered_df["group_name"] = filtered_df["group_id"].map(groups_dict).fillna(filtered_df["group_id"])
    else:
        filtered_df = filtered_df.copy()
        filtered_df["group_name"] = filtered_df["group_id"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Всего комментариев", len(filtered_df))
    
    with col2:
        st.metric("Уникальных авторов", filtered_df["author_name"].nunique())
    
    with col3:
        st.metric("Групп", filtered_df["group_id"].nunique())
    
    with col4:
        st.metric("Обсуждений", filtered_df["discussion_id"].nunique())
    
    st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 По датам",
        "👥 Топ авторов",
        "🔥 Активность",
        "📋 Данные",
    ])
    
    with tab1:
        render_comments_by_date(filtered_df)
    
    with tab2:
        limit = st.slider("Количество авторов", 5, 50, 10)
        render_top_authors(filtered_df, limit=limit)
    
    with tab3:
        render_comments_heatmap(filtered_df)
    
    with tab4:
        st.subheader("Последние комментарии")
        
        display_cols = ["group_name", "author_name", "discussion_text", "text", "created_at", "discussion_id"]
        available_cols = [c for c in display_cols if c in filtered_df.columns]
        
        if available_cols:
            st.dataframe(
                filtered_df[available_cols]
                .sort_values("created_at", ascending=False)
                .head(100),
                use_container_width=True,
            )
        
        if st.button("Экспорт CSV"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                "Скачать CSV",
                csv,
                "comments.csv",
                "text/csv",
            )


if __name__ == "__main__":
    main()
