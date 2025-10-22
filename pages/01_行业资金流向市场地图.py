import streamlit as st
import plotly.express as px
import pandas as pd
import io
import requests
from bs4 import BeautifulSoup
import py_mini_racer
# --- 数据抓取函数  ---
@st.cache_data(ttl=600)
def get_zijindongxiang_data():
    try:
        from akshare.datasets import get_ths_js
        js_file_path = get_ths_js("ths.js")
    except ImportError:
        st.error("请安装 akshare 库: pip install akshare")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"无法获取 ths.js 文件: {e}")
        return pd.DataFrame()
    def _get_file_content_ths(file_path: str) -> str:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    js_code = py_mini_racer.MiniRacer()
    js_content = _get_file_content_ths(js_file_path)
    js_code.eval(js_content)
    v_code = js_code.call("v")
    headers = {
        "Accept": "text/html, */*; q=0.01", "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Cache-Control": "no-cache",
        "Connection": "keep-alive", "hexin-v": v_code, "Host": "data.10jqka.com.cn",
        "Pragma": "no-cache", "Referer": "http://data.10jqka.com.cn/funds/hyzjl/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }
    initial_url = "http://data.10jqka.com.cn/funds/hyzjl/field/tradezdf/order/desc/ajax/1/free/1/"
    try:
        r = requests.get(initial_url, headers=headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, features="lxml")
        raw_page = soup.find(name="span", attrs={"class": "page_info"}).text
        page_num = int(raw_page.split("/")[1])
    except Exception as e:
        st.error(f"获取页码信息失败: {e}")
        return pd.DataFrame()
    url_template = "http://data.10jqka.com.cn/funds/hyzjl/field/tradezdf/order/desc/ajax/1/free/{}/"
    big_df = pd.DataFrame()
    progress_bar = st.progress(0, text="正在抓取数据...")
    for i, page in enumerate(range(1, page_num + 1)):
        current_url = url_template.format(page)
        try:
            r = requests.get(current_url, headers=headers)
            r.raise_for_status()
            temp_df = pd.read_html(io.StringIO(r.text))[0]
            big_df = pd.concat(objs=[big_df, temp_df], ignore_index=True)
        except Exception as e:
            st.warning(f"第 {page} 页抓取失败，已跳过。错误: {e}")
            continue
        finally:
            progress_bar.progress((i + 1) / page_num, text=f"正在抓取第 {i + 1}/{page_num} 页...")
    progress_bar.empty()
    # --- 关键修复：在返回数据前进行去重 ---
    # 这将移除所有完全重复的行，确保数据唯一性。
    if not big_df.empty:
        big_df.drop_duplicates(inplace=True)
    return big_df
# --- Streamlit 应用主体 ---
st.set_page_config(layout="wide", page_title="行业资金流向热力图")
st.title("行业资金流向市场地图")
st.markdown("数据来源：同花顺 (data.10jqka.com.cn)")
# --- 侧边栏控件 ---
st.sidebar.header("控制面板")
chart_type = st.sidebar.radio("选择图表类型", ("市场地图", "散点图"), index=0)
color_by_option = st.sidebar.selectbox("热力图颜色代表", ("净额(亿)", "流入资金(亿)"), index=0)
size_by_option = st.sidebar.selectbox("热力图大小代表", ("净额(亿)", "流入资金(亿)"), index=0)
st.sidebar.markdown("---")
st.sidebar.subheader("图表排序依据")
sort_options = {
    "行业名称": "行业名称", "行业涨跌幅(%)": "行业涨跌幅", "净额(亿)": "净额(亿)",
    "流入资金(亿)": "流入资金(亿)", "公司家数": "公司家数", "领涨股涨跌幅(%)": "领涨股涨跌幅",
}
sort_by_col = st.sidebar.selectbox("排序依据", options=list(sort_options.keys()), index=2)
sort_ascending = st.sidebar.checkbox("升序排列", value=False)
# --- 数据加载与处理 ---
if st.sidebar.button("获取最新数据", type="primary"):
    st.cache_data.clear()
with st.spinner("正在加载数据，请稍候..."):
    df = get_zijindongxiang_data()
if df.empty:
    st.error("未能获取到数据，请检查网络连接或稍后重试。")
    st.stop()
# --- 数据清洗和准备 ---
column_map = {
    '行业': '行业名称', '涨跌幅': '行业涨跌幅', '流入资金(亿)': '流入资金(亿)',
    '流出资金(亿)': '流出资金(亿)', '净额(亿)': '净额(亿)', '公司家数': '公司家数',
    '领涨股': '领涨股', '涨跌幅.1': '领涨股涨跌幅', '当前价(元)': '当前价(元)',
}
df.rename(columns=column_map, inplace=True)
def clean_numeric_series(series):
    if series.dtype == 'object':
        series = series.astype(str).str.replace('%', '', regex=False)
        series = series.str.replace('--', '0', regex=False)
        series = series.str.replace(',', '', regex=False)
    return pd.to_numeric(series, errors='coerce')
numeric_cols_to_clean = [
    '行业涨跌幅', '流入资金(亿)', '流出资金(亿)', '净额(亿)',
    '公司家数', '领涨股涨跌幅', '当前价(元)'
]
for col in numeric_cols_to_clean:
    if col in df.columns:
        df[col] = clean_numeric_series(df[col])
# 根据用户选择对数据进行排序，用于图表
df_plot = df.sort_values(by=sort_options[sort_by_col], ascending=sort_ascending)
# 用于数据表的排序后的DataFrame
df_table = df_plot.copy()
# --- 绘制图表 ---
st.subheader(f"行业资金流向 ({chart_type})")
color_col = '行业涨跌幅' if color_by_option == "行业涨跌幅(%)" else '净额(亿)'
size_col = '净额(亿)' if size_by_option == "净额(亿)" else '公司家数'
# 添加绝对值列用于大小
df_plot['净额(亿)_abs'] = df_plot['净额(亿)'].abs()
df_plot[size_col + '_abs'] = df_plot[size_col].abs()
df_plot.dropna(subset=[color_col, size_col + '_abs'], inplace=True)
if df_plot.empty:
    st.error("绘图数据为空，可能是因为关键列（如净额或涨跌幅）包含无效数据。")
    st.stop()
if chart_type == "市场地图":
    st.caption("注意：市场地图的布局由算法根据块的大小和颜色自动决定，不完全等同于列表排序。")
    fig = px.treemap(
        df_plot,
        path=[px.Constant("所有行业"), '行业名称'],
        values=size_col + '_abs',
        color=color_col,
        color_continuous_scale='RdYlGn_r',  # 红色代表热门
        hover_data={
            '行业涨跌幅': ':.2f%', '净额(亿)': ':.2f', '领涨股': True, '领涨股涨跌幅': ':.2f%'
        },
        title=f"颜色: {color_by_option} | 大小: {size_by_option} (绝对值)"
    )
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>行业涨跌幅: %{customdata[0]}<br>净额: %{customdata[1]} 亿<br>领涨股: %{customdata[2]} (%{customdata[3]})<extra></extra>'
    )
    fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
    st.plotly_chart(fig, use_container_width=True)
# --- 方案2: 散点图 ---
elif chart_type == "散点图":
    fig = px.scatter(
        df_plot,
        x='公司家数',
        y='行业名称',
        size=size_col + '_abs',
        color=color_col,
        color_continuous_scale='RdYlGn_r',
        hover_data={
            '行业涨跌幅': ':.2f%', '净额(亿)': ':.2f', '领涨股': True, '领涨股涨跌幅': ':.2f%'
        },
        title=f"颜色: {color_by_option} | 大小: {size_by_option} (绝对值) | X轴: 公司家数"
    )
    fig.update_traces(
        hovertemplate='<b>%{y}</b><br>公司家数: %{x}<br>行业涨跌幅: %{customdata[0]}<br>净额: %{customdata[1]} 亿<br>领涨股: %{customdata[2]} (%{customdata[3]})<extra></extra>'
    )
    fig.update_layout(
        yaxis={'categoryorder': 'array', 'categoryarray': df_plot['行业名称'].tolist()},
        height=800
    )
    st.plotly_chart(fig, use_container_width=True)
# --- 显示原始数据表格 ---
st.subheader("详细数据表")
st.dataframe(df_table, use_container_width=True)
