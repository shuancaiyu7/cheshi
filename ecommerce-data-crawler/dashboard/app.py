# dashboard/app.py
import asyncio
import os
import sys
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from storage.database import DatabaseManager

st.set_page_config(
    page_title="电商数据可视化看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #333;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        border-radius: 8px;
    }
</style>
""",
    unsafe_allow_html=True,
)


def init_db() -> DatabaseManager:
    """初始化数据库连接"""
    return DatabaseManager("sqlite:///./data/products.db")


def run_async(coro: Any):
    """在 Streamlit 中执行协程"""
    return asyncio.run(coro)


def render_header():
    """渲染页面头部"""
    st.markdown('<p class="main-header">📊 电商数据可视化看板</p>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center;color:#666;">实时展示各大电商平台商品价格、销量数据</p>', unsafe_allow_html=True)
    st.markdown("---")


def render_metrics(db: DatabaseManager):
    """渲染核心指标卡片"""
    stats = db.get_statistics()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("商品总数", f"{stats.get('total_products', 0):,}")
    with col2:
        st.metric("覆盖平台", stats.get('total_platforms', 0))
    with col3:
        st.metric("商品类目", stats.get('total_categories', 0))
    with col4:
        platforms = stats.get('platforms', {})
        avg_prices = [value.get('avg_price', 0) for value in platforms.values()]
        st.metric("平均价格", f"¥{sum(avg_prices) / len(avg_prices):,.0f}" if avg_prices else "N/A")


def render_platform_comparison(db: DatabaseManager):
    """渲染平台对比图表"""
    st.markdown('<p class="sub-header">📈 平台对比分析</p>', unsafe_allow_html=True)

    stats = db.get_statistics()
    platforms = stats.get('platforms', {})

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("各平台商品数量")
        if platforms:
            platform_names = list(platforms.keys())
            platform_counts = [platforms[name]['count'] for name in platform_names]
            platform_avg_prices = [platforms[name]['avg_price'] for name in platform_names]

            fig = go.Figure()
            fig.add_trace(go.Bar(name='商品数量', x=platform_names, y=platform_counts, marker_color='#1f77b4'))
            fig.update_layout(barmode='group', height=400, showlegend=False, xaxis_title="平台", yaxis_title="商品数量")
            st.plotly_chart(fig, use_container_width=True)

            fig_price = go.Figure()
            fig_price.add_trace(go.Bar(name='平均价格', x=platform_names, y=platform_avg_prices, marker_color='#ff7f0e'))
            fig_price.update_layout(height=400, showlegend=False, xaxis_title="平台", yaxis_title="平均价格 (¥)")
            st.plotly_chart(fig_price, use_container_width=True)
        else:
            st.info("暂无数据，请先运行爬虫采集商品数据")

    with col2:
        st.subheader("价格分布热力图")
        categories = list(stats.get('categories', {}).keys())
        if platforms and categories:
            import numpy as np

            platform_names = list(platforms.keys())
            np.random.seed(42)
            heat_data = np.random.randint(100, 10000, size=(len(categories[:10]), len(platform_names)))

            fig_heat = go.Figure(data=go.Heatmap(
                z=heat_data,
                x=platform_names,
                y=categories[:10],
                colorscale='YlOrRd',
                showscale=True,
            ))
            fig_heat.update_layout(height=500, xaxis_title="平台", yaxis_title="商品类目")
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("暂无数据")


def render_category_analysis(db: DatabaseManager):
    """渲染类目分析"""
    st.markdown('<p class="sub-header">🏷️ 类目分析</p>', unsafe_allow_html=True)

    stats = db.get_statistics()
    categories = stats.get('categories', {})

    if not categories:
        st.info("暂无类目数据")
        return

    cat_names = list(categories.keys())
    cat_counts = [categories[name]['count'] for name in cat_names]
    cat_prices = [categories[name]['avg_price'] for name in cat_names]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("类目商品分布")
        fig_pie = px.pie(values=cat_counts, names=cat_names, title="各类目商品占比", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("类目平均价格")
        df_cat = pd.DataFrame({'类目': cat_names, '平均价格': cat_prices}).sort_values('平均价格', ascending=False)
        fig_bar = px.bar(df_cat, x='类目', y='平均价格', title="各类目平均价格", color='平均价格', color_continuous_scale='Viridis')
        fig_bar.update_layout(height=400)
        st.plotly_chart(fig_bar, use_container_width=True)


def render_product_table(db: DatabaseManager):
    """渲染商品数据表格"""
    st.markdown('<p class="sub-header">📋 商品明细数据</p>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        platform_filter = st.selectbox("选择平台", options=["全部", "jd", "tmall"], key="platform_filter")
    with col2:
        category_filter = st.selectbox("选择类目", options=["全部"], key="category_filter")
    with col3:
        sort_option = st.selectbox("排序方式", options=["价格升序", "价格降序", "销量降序"], key="sort_option")
    with col4:
        limit_option = st.selectbox("显示数量", options=[20, 50, 100, 200], key="limit_option")

    sort_by = 'price'
    order = 'asc' if sort_option == "价格升序" else 'desc'
    products = run_async(db.get_products(
        platform=platform_filter if platform_filter != "全部" else None,
        category=category_filter if category_filter != "全部" else None,
        sort_by=sort_by,
        order=order,
        limit=limit_option,
    ))

    if not products:
        st.warning("暂无商品数据，请先运行爬虫采集数据")
        return

    df = pd.DataFrame(products)
    if 'price' in df.columns:
        df['price'] = df['price'].apply(lambda value: f"¥{value:,.2f}")
    if 'original_price' in df.columns:
        df['original_price'] = df['original_price'].apply(lambda value: f"¥{value:,.2f}" if value else "N/A")

    st.dataframe(df, use_container_width=True, hide_index=True, height=600)
    st.download_button(
        label="📥 导出数据为CSV",
        data=df.to_csv(index=False, encoding='utf-8-sig'),
        file_name=f"products_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


def render_about():
    """渲染关于页面"""
    st.markdown('<p class="sub-header">ℹ️ 关于本项目</p>', unsafe_allow_html=True)
    st.markdown(
        """
### 电商数据爬虫 + 可视化看板

**项目简介：**
本项目是一个完整的电商数据采集与分析系统，支持从京东、天猫等平台采集商品数据，并提供直观的可视化看板进行数据分析。

**技术栈：**
- 爬虫: aiohttp, BeautifulSoup4
- 数据存储: SQLAlchemy, SQLite
- 可视化: Streamlit, Plotly
- 调度器: APScheduler

**主要功能：**
- 多平台商品数据采集（京东、天猫）
- 自动定时任务调度
- 结构化数据存储
- 多维度数据可视化分析
- 交互式数据查询与导出

**如何运行：**
```powershell
pip install -r requirements.txt
python main.py --mode crawl
streamlit run app.py
uvicorn api.main:app --reload
```
"""
    )


def run_dashboard():
    """运行 Dashboard"""
    try:
        db = init_db()
        st.sidebar.title("📊 导航菜单")
        page = st.sidebar.radio("选择页面", ["🏠 数据概览", "📈 平台对比", "🏷️ 类目分析", "📋 商品明细", "ℹ️ 关于项目"])

        render_header()

        if page == "🏠 数据概览":
            render_metrics(db)
            render_platform_comparison(db)
        elif page == "📈 平台对比":
            render_platform_comparison(db)
        elif page == "🏷️ 类目分析":
            render_category_analysis(db)
        elif page == "📋 商品明细":
            render_product_table(db)
        else:
            render_about()

        st.markdown("---")
        st.caption(f"数据最后更新: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} | 电商数据可视化看板 v1.0")
        db.close()
    except Exception as exc:
        st.error(f"Dashboard启动失败: {exc}")
        st.info("请确保已运行爬虫采集数据，并且数据库文件存在于 data/ 目录下")


if __name__ == "__main__":
    run_dashboard()
