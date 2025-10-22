
import streamlit as st
import pywencai
import pandas as pd
import re
from datetime import datetime, time
import plotly.express as px
import plotly.graph_objects as go
def get_market_change_data(target_date, target_time):
    """
    统计指定日期和时分的大盘涨跌幅情况
    target_date: 日期字符串，格式如 '20251014'
    target_time: 时间字符串，格式如 '09:25'
    """
    try:
        # 构建查询语句，获取指定时间的大盘数据
        query = f"{target_date} {target_time} 大盘涨跌幅,所属概念"
        # 获取数据
        df = pywencai.get(query=query, loop=True)
        st.write("数据获取结果：", df)  # 云端日志中查看是否为None
        if df is None or df.empty:
            return None
        # 模糊匹配涨跌幅字段
        change_columns = []
        patterns = [
            r'.*涨跌幅.*',
            r'.*涨幅.*',
            r'.*跌幅.*',
            r'.*涨跌.*',
            r'.*幅度.*'
        ]
        for pattern in patterns:
            matched_cols = [col for col in df.columns if re.search(pattern, col, re.IGNORECASE)]
            change_columns.extend(matched_cols)
        # 去重
        change_columns = list(set(change_columns))
        if not change_columns:
            return None
        # 选择最相关的涨跌幅列
        selected_column = None
        for col in change_columns:
            if '分时' in col or target_time.replace(':', '') in col or target_time in col:
                selected_column = col
                break
        if not selected_column and change_columns:
            selected_column = change_columns[0]
        # 数据清洗和统计
        df[selected_column] = pd.to_numeric(df[selected_column], errors='coerce')
        valid_data = df[df[selected_column].notna()].copy()
        if valid_data.empty:
            return None
        # 基本统计信息
        total_count = len(valid_data)
        up_count = len(valid_data[valid_data[selected_column] > 0])
        down_count = len(valid_data[valid_data[selected_column] < 0])
        flat_count = len(valid_data[valid_data[selected_column] == 0])
        up_ratio = (up_count / total_count) * 100 if total_count > 0 else 0
        down_ratio = (down_count / total_count) * 100 if total_count > 0 else 0
        flat_ratio = (flat_count / total_count) * 100 if total_count > 0 else 0
        max_increase = valid_data[selected_column].max()
        min_increase = valid_data[selected_column].min()
        avg_increase = valid_data[selected_column].mean()
        max_stock = valid_data.loc[valid_data[selected_column].idxmax()]
        min_stock = valid_data.loc[valid_data[selected_column].idxmin()]
        # 涨停跌停统计
        limit_up = valid_data[valid_data[selected_column] >= 9.9].copy()
        limit_down = valid_data[valid_data[selected_column] <= -9.9].copy()
        # 提取概念信息
        def extract_concepts(concept_str):
            if pd.isna(concept_str):
                return []
            return [c.strip() for c in re.split(r'[,;，；]', concept_str) if c.strip()]
        # 涨停概念统计
        limit_up_concepts = []
        for _, row in limit_up.iterrows():
            concepts = extract_concepts(row.get('所属概念', ''))
            for concept in concepts:
                limit_up_concepts.append({
                    '股票代码': row.get('股票代码', ''),
                    '股票简称': row.get('股票简称', ''),
                    '涨跌幅': row[selected_column],
                    '概念': concept
                })
        # 跌停概念统计
        limit_down_concepts = []
        for _, row in limit_down.iterrows():
            concepts = extract_concepts(row.get('所属概念', ''))
            for concept in concepts:
                limit_down_concepts.append({
                    '股票代码': row.get('股票代码', ''),
                    '股票简称': row.get('股票简称', ''),
                    '涨跌幅': row[selected_column],
                    '概念': concept
                })
        # 按涨跌幅区间统计
        bins = [-float('inf'), -5, -3, -1, 0, 1, 3, 5, float('inf')]
        labels = ['<-5%', '-5%至-3%', '-3%至-1%', '0%', '0%至1%', '1%至3%', '3%至5%', '>5%']
        range_stats = pd.cut(valid_data[selected_column], bins=bins, labels=labels).value_counts().sort_index()
        # 返回统计结果
        stats = {
            '统计日期': target_date,
            '统计时间': target_time,
            '总家数': total_count,
            '上涨家数': up_count,
            '下跌家数': down_count,
            '平盘家数': flat_count,
            '上涨比例': up_ratio,
            '下跌比例': down_ratio,
            '平盘比例': flat_ratio,
            '最大涨幅': max_increase,
            '最大跌幅': min_increase,
            '平均涨跌幅': avg_increase,
            '涨跌幅列名': selected_column,
            '涨停数量': len(limit_up),
            '跌停数量': len(limit_down),
            '涨停股票': limit_up[['股票代码', '股票简称', selected_column, '所属概念']].copy(),
            '跌停股票': limit_down[['股票代码', '股票简称', selected_column, '所属概念']].copy(),
            '涨停概念': pd.DataFrame(limit_up_concepts),
            '跌停概念': pd.DataFrame(limit_down_concepts),
            '区间分布': range_stats,
            '详细数据': valid_data[['股票代码', '股票简称', selected_column, '所属概念']].copy()
        }
        return stats
    except Exception as e:
        st.error(f"统计过程中发生错误: {e}")
        return None
# Streamlit 应用
st.set_page_config(
    page_title="大盘涨跌统计",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)
# 左侧边栏 - 查询控制
with st.sidebar:
    st.title("🔍 查询控制")
    st.markdown("---")
    # 日期选择
    st.subheader("📅 选择日期")
    selected_date = st.date_input(
        "统计日期",
        datetime.now().date(),
        help="选择要统计的日期"
    )
    # 时间选择
    st.subheader("🕐 选择时间")
    # 预设时间选项
    time_options = {
        "开盘前集合竞价 (09:25)": "09:25",
        "开盘 (09:30)": "09:30",
        "早盘收盘 (11:30)": "11:30",
        "午盘开盘 (13:00)": "13:00",
        "收盘前 (14:57)": "14:57",
        "收盘 (15:00)": "15:00",
        "自定义时间": None
    }
    selected_option = st.selectbox(
        "选择预设时间",
        list(time_options.keys()),
        help="选择常用时间点或自定义时间"
    )
    # 根据选择设置时间
    if selected_option == "自定义时间":
        selected_time = st.time_input(
            "自定义时间",
            value=time(9, 25),
            help="选择具体的时分"
        )
        target_time = selected_time.strftime("%H:%M")
    else:
        target_time = time_options[selected_option]
        st.info(f"已选择时间: {target_time}")
    # 查询按钮
    st.markdown("---")
    if st.button("🚀 开始统计", type="primary", use_container_width=True):
        target_date = selected_date.strftime('%Y%m%d')
        with st.spinner(f"正在获取 {target_date} {target_time} 的数据..."):
            result = get_market_change_data(target_date, target_time)
        if result is None:
            st.session_state.stats_result = None
            st.error("未获取到数据，请检查日期和时间是否有效")
        else:
            st.session_state.stats_result = result
            st.success(f"✅ 成功获取数据")
            st.balloons()
    # 显示当前查询状态
    st.markdown("---")
    st.subheader("📊 查询状态")
    if 'stats_result' in st.session_state and st.session_state.stats_result:
        result = st.session_state.stats_result
        st.info(f"已加载 {result['统计日期']} {result['统计时间']} 数据")
        st.metric("总家数", result['总家数'])
        st.metric("涨停数", result['涨停数量'])
        st.metric("跌停数", result['跌停数量'])
    else:
        st.warning("暂无数据，请先查询")
    # 查询提示
    st.markdown("---")
    st.markdown("""
    <div style='font-size: 12px; color: gray;'>
    <p><strong>提示：</strong></p>
    <ul>
    <li>交易时间：09:30-11:30, 13:00-15:00</li>
    <li>集合竞价：09:15-09:25</li>
    <li>建议选择整点或半点时间</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
# 主区域 - 内容展示
st.title("📈 大盘涨跌统计")
st.markdown("统计指定日期和时分的大盘涨跌情况，包括涨停跌停股票及其概念分布")
# 检查是否有数据
if 'stats_result' in st.session_state and st.session_state.stats_result:
    result = st.session_state.stats_result
    # 显示查询的日期时间
    st.markdown(f"### 📊 {result['统计日期']} {result['统计时间']} 市场统计")
    # 使用tabs组织内容
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 概览",
        "🚨 涨停跌停",
        "📈 概念分析",
        "📋 详细数据"
    ])
    with tab1:
        # 概览页面
        st.header("📊 市场概览")
        # 关键指标卡片
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📈 上涨家数", f"{result['上涨家数']}", f"{result['上涨比例']:.2f}%")
        with col2:
            st.metric("📉 下跌家数", f"{result['下跌家数']}", f"{result['下跌比例']:.2f}%", delta_color="inverse")
        with col3:
            st.metric("🔴 涨停数", f"{result['涨停数量']}")
        with col4:
            st.metric("🟢 跌停数", f"{result['跌停数量']}")
        st.markdown("---")
        # 涨跌幅统计
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⬆️ 最大涨幅", f"{result['最大涨幅']:.2f}%")
        with col2:
            st.metric("⬇️ 最大跌幅", f"{result['最大跌幅']:.2f}%")
        with col3:
            st.metric("📊 平均涨跌", f"{result['平均涨跌幅']:.2f}%")
        # 区间分布图
        st.markdown("---")
        st.subheader("📊 涨跌幅区间分布")
        range_df = pd.DataFrame({
            '区间': result['区间分布'].index,
            '数量': result['区间分布'].values,
            '比例': (result['区间分布'].values / result['总家数'] * 100).round(2)
        })
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='数量',
            x=range_df['区间'],
            y=range_df['数量'],
            marker_color='lightblue'
        ))
        fig.add_trace(go.Scatter(
            name='比例(%)',
            x=range_df['区间'],
            y=range_df['比例'],
            mode='lines+markers',
            line=dict(color='firebrick', width=3),
            yaxis='y2'
        ))
        fig.update_layout(
            title="涨跌幅区间分布",
            xaxis_title="涨跌幅区间",
            yaxis=dict(title="数量", side="left"),
            yaxis2=dict(title="比例(%)", overlaying="y", side="right"),
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        # 涨停跌停页面
        st.header("🚨 涨停跌停分析")
        st.subheader(f"🔴 涨停股票 ({result['涨停数量']}家)")
        if not result['涨停股票'].empty:
            st.dataframe(
                result['涨停股票'],
                use_container_width=True,
                hide_index=True,
                height=500
            )
        else:
            st.info("该时间点无涨停股票")
        st.subheader(f"🟢 跌停股票 ({result['跌停数量']}家)")
        if not result['跌停股票'].empty:
            st.dataframe(
                result['跌停股票'],
                use_container_width=True,
                hide_index=True,
                height=500
            )
        else:
            st.info("该时间点无跌停股票")
    with tab3:
        # 概念分析页面
        st.header("📈 概念板块分析")
        if not result['涨停概念'].empty or not result['跌停概念'].empty:
            col1, col2 = st.columns(2)
            with col1:
                if not result['涨停概念'].empty:
                    st.subheader("🔴 涨停概念TOP15")
                    concept_counts = result['涨停概念']['概念'].value_counts().head(15)
                    fig = px.bar(
                        x=concept_counts.values,
                        y=concept_counts.index,
                        orientation='h',
                        labels={'x': '涨停数量', 'y': '概念'},
                        title="涨停概念分布"
                    )
                    fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    with st.expander("查看详情"):
                        st.dataframe(result['涨停概念'], hide_index=True)
            with col2:
                if not result['跌停概念'].empty:
                    st.subheader("🟢 跌停概念TOP15")
                    concept_counts = result['跌停概念']['概念'].value_counts().head(15)
                    fig = px.bar(
                        x=concept_counts.values,
                        y=concept_counts.index,
                        orientation='h',
                        labels={'x': '跌停数量', 'y': '概念'},
                        title="跌停概念分布"
                    )
                    fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    with st.expander("查看详情"):
                        st.dataframe(result['跌停概念'], hide_index=True)
        else:
            st.info("该时间点暂无涨停跌停概念数据")
    with tab4:
        # 详细数据页面
        st.header("📋 详细数据")
        # 数据概览
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("记录数", len(result['详细数据']))
        with col2:
            st.metric("统计日期", result['统计日期'])
        with col3:
            st.metric("统计时间", result['统计时间'])
        with col4:
            st.metric("数据列", result['涨跌幅列名'])
        # 数据表格
        st.markdown("---")
        st.subheader("完整数据列表")
        st.dataframe(
            result['详细数据'],
            use_container_width=True,
            hide_index=True,
            height=500
        )
        # 下载按钮
        csv = result['详细数据'].to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下载CSV文件",
            data=csv,
            file_name=f"{result['统计日期']}_{result['统计时间'].replace(':', '')}_market_data.csv",
            mime="text/csv",
            use_container_width=True
        )
else:
    # 无数据时的提示
    st.markdown("---")
    st.info("👈 请在左侧选择日期和时间并点击'开始统计'按钮查询数据")
