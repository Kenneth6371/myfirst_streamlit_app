import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 初始化session_state存储数据
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None

# 定义函数：获取上一个周五的日期（格式YYYYMMDD）
def get_last_friday():
    today = datetime.now()
    last_friday = today - timedelta(days=1)
    # 循环往前找，直到找到周五（weekday=4，周一为0，周日为6）
    while last_friday.weekday() != 4:
        last_friday -= timedelta(days=1)
    return last_friday.strftime("%Y%m%d")

# 设置页面配置
st.set_page_config(
    layout="wide",
    page_title="申万指数周度分析",
    page_icon="📊"
)

# 页面标题和说明
st.title("申万指数周度分析工具")
st.markdown("基于akshare接口获取申万指数周度分析数据，展示涨跌幅指标的柱状图")

# 侧边栏参数设置
st.sidebar.header("参数设置")

# 选择分析类型
symbol = st.sidebar.selectbox(
    "分析类型",
    options=["市场表征", "一级行业", "二级行业", "风格指数"],
    index=0,
    key="symbol_select"
)

# 日期输入（默认值为上一个周五）
date = st.sidebar.text_input(
    "日期（格式：YYYYMMDD）",
    value=get_last_friday(),  # 调用函数设置默认日期
    key="date_input"
)

# 获取数据按钮
get_data = st.sidebar.button("获取数据", type="primary", key="get_data_btn")

# 缓存数据获取函数
@st.cache_data(ttl=3600)
def get_index_analysis_data(symbol, date):
    """获取申万指数周度分析数据"""
    try:
        df = ak.index_analysis_weekly_sw(symbol=symbol, date=date)
        return df
    except Exception as e:
        st.error(f"数据获取失败: {str(e)}")
        return None

# 处理数据获取逻辑
if get_data  or st.session_state.analysis_data is None:
    with st.spinner("正在获取数据，请稍候..."):
        st.session_state.analysis_data = get_index_analysis_data(symbol, date)

# 展示数据和图表
if st.session_state.analysis_data is not None and not st.session_state.analysis_data.empty:
    if "涨跌幅" not in st.session_state.analysis_data.columns:
        st.error("数据中未找到'涨跌幅'列，请检查数据结构或尝试其他日期")
        st.stop()
    
    st.subheader(f"{symbol} - {date} 原始数据")
    st.dataframe(st.session_state.analysis_data, use_container_width=True)
    
    # 固定使用涨跌幅数据并按降序排列
    metric = "涨跌幅"
    # 按涨跌幅降序排序
    sorted_df = st.session_state.analysis_data.sort_values(
        by=metric,
        ascending=False  # 固定降序
    )
    
    # 绘制普通柱状图（垂直方向）
    fig = px.bar(
        sorted_df,
        x=sorted_df.columns[1],  # 类别列作为x轴
        y=metric,                # 涨跌幅作为y轴
        title=f"{symbol} {metric} 柱状图（降序）",
        labels={metric: f"{metric}(%)", sorted_df.columns[0]: sorted_df.columns[0]},
        color=metric,
        color_continuous_scale=["green", "white", "red"],  # 跌绿涨红
        color_continuous_midpoint=0  # 中点为0
    )
    
    # 美化图表：旋转x轴标签避免重叠
    fig.update_layout(
        height=600,
        xaxis_tickangle=-45,  # x轴标签旋转45度
        margin=dict(b=150)    # 底部留白，避免标签被截断
    )
    
    st.plotly_chart(fig, use_container_width=True)
elif get_data:
    st.warning("未获取到有效数据，请检查参数是否正确")
else:
    st.info("请在左侧设置参数并点击'获取数据'按钮")

# 显示数据来源信息
st.caption("数据来源：akshare - 申万指数周度分析接口")
    