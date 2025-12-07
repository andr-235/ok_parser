import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple


def render_group_filter(df: pd.DataFrame, df_groups: Optional[pd.DataFrame] = None) -> Optional[str]:
    if df.empty or "group_id" not in df.columns:
        return None
    
    group_ids = sorted(df["group_id"].unique().tolist())
    group_map = {}
    group_options = ["Все"]
    
    if df_groups is not None and not df_groups.empty and "uid" in df_groups.columns:
        groups_dict = dict(zip(df_groups["uid"], df_groups["name"]))
        for gid in group_ids:
            group_name = groups_dict.get(gid, None)
            if group_name:
                label = f"{group_name} ({gid})"
            else:
                label = gid
            group_options.append(label)
            group_map[label] = gid
    else:
        for gid in group_ids:
            group_options.append(gid)
            group_map[gid] = gid
    
    selected = st.selectbox("Группа", group_options, index=0)
    
    if selected == "Все":
        return None
    
    return group_map.get(selected, selected)


def render_date_filter(
    df: pd.DataFrame,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    if df.empty or "created_at" not in df.columns:
        return None, None
    
    df["created_at"] = pd.to_datetime(df["created_at"])
    
    min_date = df["created_at"].min().date()
    max_date = df["created_at"].max().date()
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "От",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
        )
    
    with col2:
        end_date = st.date_input(
            "До",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
        )
    
    return (
        datetime.combine(start_date, datetime.min.time()),
        datetime.combine(end_date, datetime.max.time()),
    )


def render_author_filter(df: pd.DataFrame) -> Optional[str]:
    if df.empty or "author_name" not in df.columns:
        return None
    
    authors = ["Все"] + sorted(df["author_name"].unique().tolist())
    selected = st.selectbox("Автор", authors, index=0)
    
    return None if selected == "Все" else selected


def apply_filters(
    df: pd.DataFrame,
    group_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    author: Optional[str] = None,
) -> pd.DataFrame:
    filtered = df.copy()
    
    if group_id:
        filtered = filtered[filtered["group_id"] == group_id]
    
    if start_date:
        filtered = filtered[pd.to_datetime(filtered["created_at"]) >= start_date]
    
    if end_date:
        filtered = filtered[pd.to_datetime(filtered["created_at"]) <= end_date]
    
    if author:
        filtered = filtered[filtered["author_name"] == author]
    
    return filtered

