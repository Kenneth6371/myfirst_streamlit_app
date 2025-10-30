import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# 设置页面配置
st.set_page_config(layout="wide", page_title="格雷厄姆指数计算器")
st.title("格雷厄姆指数（股债性价比）分析工具")
st.markdown("格雷厄姆指数 = 盈利收益率 / 10年期国债收益率 = (1/滚动市盈率) / 10年期国债收益率")

# 侧边栏控件
st.sidebar.header("参数设置")
index_option = st.sidebar.selectbox(
    "选择指数",
    ["上证50", "沪深300", "中证500", "创业板指"],
    index=0
)

# 时间范围选择
date_range = st.sidebar.slider(
    "数据时间范围（天）",
    min_value=30,
    max_value=365*5,
    value=365,
    step=30
)

# 缓存数据获取函数
@st.cache_data(ttl=3600)  # 每小时更新一次缓存
def get_index_pe_data(index_name, days):
    """获取指数的滚动市盈率数据"""
    try:
        # 根据选择的指数获取对应的symbol
        index_symbol_map = {
            "上证50": "上证50",
            "沪深300": "沪深300",
            "中证500": "中证500",
            "创业板指": "创业板指"
        }
        symbol = index_symbol_map[index_name]
        
        # 计算起始日期
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        
        # 获取数据
        index_pe_df = ak.stock_index_pe_lg(symbol=symbol)
        
        # 确保日期列格式正确并筛选时间范围
        index_pe_df["日期"] = pd.to_datetime(index_pe_df["日期"])
        mask = (index_pe_df["日期"] >= start_date) & (index_pe_df["日期"] <= end_date)
        filtered_df = index_pe_df[mask].copy()
        
        return filtered_df
    except Exception as e:
        st.error(f"获取指数市盈率数据失败: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_bond_yield_data(days):
    """获取国债收益率数据（修正：移除end_date参数，通过筛选获取时间范围）"""
    try:
        # 计算起始和结束日期
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 获取数据（注意：该接口没有end_date参数，只传start_date）
        bond_yield_df = ak.bond_zh_us_rate(start_date=start_date.strftime("%Y%m%d"))
        
        # 确保日期列格式正确并筛选时间范围
        bond_yield_df["日期"] = pd.to_datetime(bond_yield_df["日期"])
        # 筛选出在时间范围内的数据
        mask = (bond_yield_df["日期"] >= start_date) & (bond_yield_df["日期"] <= end_date)
        filtered_df = bond_yield_df[mask].copy()
        
        return filtered_df
    except Exception as e:
        st.error(f"获取国债收益率数据失败: {e}")
        return pd.DataFrame()

# 数据获取与处理
with st.spinner("正在获取数据，请稍候..."):
    # 获取数据
    index_pe_df = get_index_pe_data(index_option, date_range)
    bond_yield_df = get_bond_yield_data(date_range)

# 检查数据是否有效
if index_pe_df.empty or bond_yield_df.empty:
    st.error("无法获取有效数据，请检查网络连接或稍后重试。")
    st.stop()

# 数据合并与计算
try:
    # 合并数据
    merged_df = pd.merge(
        index_pe_df[["日期", "滚动市盈率"]],
        bond_yield_df[["日期", "中国国债收益率10年"]],
        on="日期",
        how="inner"
    )
    
    # 计算格雷厄姆指数相关指标
    merged_df["盈利收益率"] = 1 / merged_df["滚动市盈率"]  # 盈利收益率 = 1/滚动市盈率
    merged_df["中国国债收益率10年_小数"] = merged_df["中国国债收益率10年"] / 100  # 转换为小数
    merged_df["格雷厄姆指数"] = merged_df["盈利收益率"] / merged_df["中国国债收益率10年_小数"]
    
    # 显示最新数据
    latest_data = merged_df.iloc[-1]
    st.subheader(f"{index_option}最新指标")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("滚动市盈率", f"{latest_data['滚动市盈率']:.2f}")
    with col2:
        st.metric("10年期国债收益率", f"{latest_data['中国国债收益率10年']:.2f}%")
    with col3:
        st.metric("盈利收益率", f"{latest_data['盈利收益率']:.2%}")
    with col4:
        st.metric("格雷厄姆指数", f"{latest_data['格雷厄姆指数']:.2f}")

except Exception as e:
    st.error(f"数据处理出错: {e}")
    st.stop()

# 绘制折线图
st.subheader(f"{index_option}相关指标趋势图")

# 图表1: 滚动市盈率和10年期国债收益率
fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=merged_df["日期"], 
    y=merged_df["滚动市盈率"],
    name="滚动市盈率",
    yaxis="y1"
))
fig1.add_trace(go.Scatter(
    x=merged_df["日期"], 
    y=merged_df["中国国债收益率10年"],
    name="10年期国债收益率(%)",
    yaxis="y2"
))

fig1.update_layout(
    title="滚动市盈率与10年期国债收益率趋势",
    yaxis=dict(title="滚动市盈率"),
    yaxis2=dict(title="10年期国债收益率(%)", overlaying="y", side="right"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=500
)
st.plotly_chart(fig1, use_container_width=True)

# 图表2: 格雷厄姆指数
fig2 = px.line(
    merged_df, 
    x="日期", 
    y="格雷厄姆指数",
    title="格雷厄姆指数(股债性价比)趋势",
    labels={"格雷厄姆指数": "格雷厄姆指数值", "日期": "日期"},
    height=500
)

# 添加参考线：格雷厄姆认为指数>2时，股票明显被低估
fig2.add_hline(
    y=2, 
    line_dash="dash", 
    line_color="green",
    annotation_text="低估参考线(2.0)",
    annotation_position="right"
)

# 添加参考线：格雷厄姆认为指数<1时，股票明显被高估
fig2.add_hline(
    y=1, 
    line_dash="dash", 
    line_color="red",
    annotation_text="高估参考线(1.0)",
    annotation_position="right"
)

st.plotly_chart(fig2, use_container_width=True)

# 显示数据表格
st.subheader("详细数据")
display_df = merged_df.copy()
display_df["盈利收益率"] = display_df["盈利收益率"].apply(lambda x: f"{x:.2%}")
display_df["中国国债收益率10年_小数"] = display_df["中国国债收益率10年_小数"].apply(lambda x: f"{x:.2%}")
st.dataframe(display_df, use_container_width=True)