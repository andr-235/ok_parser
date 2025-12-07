import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional


def render_comments_by_date(df: pd.DataFrame) -> Optional[plt.Figure]:
    if df.empty or "created_at" not in df.columns:
        st.warning("Нет данных для отображения")
        return None
    
    df["date"] = pd.to_datetime(df["created_at"]).dt.date
    daily_counts = df.groupby("date").size().reset_index(name="count")
    
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(daily_counts["date"], daily_counts["count"], color="#1E88E5")
    ax.set_xlabel("Дата")
    ax.set_ylabel("Количество комментариев")
    ax.set_title("Комментарии по датам")
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    st.pyplot(fig)
    return fig


def render_top_authors(df: pd.DataFrame, limit: int = 10) -> Optional[plt.Figure]:
    if df.empty or "author_name" not in df.columns:
        st.warning("Нет данных для отображения")
        return None
    
    top_authors = df["author_name"].value_counts().head(limit)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.Blues(range(50, 250, 200 // limit))
    ax.barh(top_authors.index[::-1], top_authors.values[::-1], color=colors)
    ax.set_xlabel("Количество комментариев")
    ax.set_ylabel("Автор")
    ax.set_title(f"Топ-{limit} авторов")
    plt.tight_layout()
    
    st.pyplot(fig)
    return fig


def render_comments_heatmap(df: pd.DataFrame) -> Optional[plt.Figure]:
    if df.empty or "created_at" not in df.columns:
        st.warning("Нет данных для отображения")
        return None
    
    df["datetime"] = pd.to_datetime(df["created_at"])
    df["hour"] = df["datetime"].dt.hour
    df["weekday"] = df["datetime"].dt.day_name()
    
    pivot = df.pivot_table(
        values="id",
        index="weekday",
        columns="hour",
        aggfunc="count",
        fill_value=0,
    )
    
    weekday_order = [
        "Monday", "Tuesday", "Wednesday", 
        "Thursday", "Friday", "Saturday", "Sunday"
    ]
    pivot = pivot.reindex([d for d in weekday_order if d in pivot.index])
    
    fig, ax = plt.subplots(figsize=(14, 5))
    im = ax.imshow(pivot.values, cmap="Blues", aspect="auto")
    
    ax.set_xticks(range(24))
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("Час")
    ax.set_ylabel("День недели")
    ax.set_title("Активность по часам и дням")
    
    plt.colorbar(im, ax=ax, label="Комментарии")
    plt.tight_layout()
    
    st.pyplot(fig)
    return fig

