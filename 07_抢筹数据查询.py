import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

# 设置页面配置
st.set_page_config(layout="wide", page_title="通达信抢筹数据查询")
st.title("通达信抢筹数据查询")
st.markdown("数据来源：通达信 (excalc.icfqs.com)")

# --- 数据获取函数 ---
@st.cache_data(ttl=300)  # 缓存5分钟
def get_chip_race_data(race_type: str, date: str = "") -> pd.DataFrame:
    """
    获取抢筹数据
    :param race_type: 抢筹类型，"open"表示早盘，"end"表示尾盘
    :param date: 日期，格式YYYYMMDD，空表示当天
    :return: 抢筹数据DataFrame
    """
    url = "http://excalc.icfqs.com:7616/TQLEX?Entry=HQServ.hq_nlp"
    period = 0 if race_type == "open" else 1
    
    try:
        if date == "":
            params = [{"funcId": 20, "offset": 0, "count": 100, "sort": 1, 
                      "period": period, "Token": "6679f5cadca97d68245a086793fc1bfc0a50b487487c812f", 
                      "modname": "JJQC"}]
        else:
            params = [{"funcId": 20, "offset": 0, "count": 100, "sort": 1, 
                      "period": period, "Token": "6679f5cadca97d68245a086793fc1bfc0a50b487487c812f", 
                      "modname": "JJQC", "date": date}]
        
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36 TdxW",
        }
        
        r = requests.post(url, json=params, headers=headers)
        r.raise_for_status()  # 检查请求是否成功
        data_json = r.json()
        data = data_json.get("datas", [])
        
        if not data:
            st.warning("未获取到数据")
            return pd.DataFrame()
        
        temp_df = pd.DataFrame(data)
        
        # 处理早盘和尾盘的不同列名
        if race_type == "open":
            temp_df.columns = [
                "代码", "名称", "昨收", "今开", "开盘金额", 
                "抢筹幅度", "抢筹委托金额", "抢筹成交金额", "最新价", "_"
            ]
            amount_col = "开盘金额"
        else:
            temp_df.columns = [
                "代码", "名称", "昨收", "今开", "收盘金额", 
                "抢筹幅度", "抢筹委托金额", "抢筹成交金额", "最新价", "_"
            ]
            amount_col = "收盘金额"
        
        # 数据清洗和转换
        temp_df["昨收"] = temp_df["昨收"] / 10000
        temp_df["今开"] = temp_df["今开"] / 10000
        temp_df["抢筹幅度"] = round(temp_df["抢筹幅度"] * 100, 2)
        temp_df["最新价"] = round(temp_df["最新价"], 2)
        temp_df["涨跌幅"] = round((temp_df["最新价"] / temp_df["昨收"] - 1) * 100, 2)
        temp_df["抢筹占比"] = round((temp_df["抢筹成交金额"] / temp_df[amount_col]) * 100, 2)
        
        # 选择需要展示的列
        columns = [
            "代码", "名称", "最新价", "涨跌幅", "昨收", "今开",
            amount_col, "抢筹幅度", "抢筹委托金额", "抢筹成交金额", "抢筹占比"
        ]
        temp_df = temp_df[columns]
        
        return temp_df
    
    except requests.exceptions.RequestException as e:
        st.error(f"网络请求错误: {str(e)}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"数据处理错误: {str(e)}")
        return pd.DataFrame()

# --- 侧边栏控件 ---
st.sidebar.header("查询设置")
race_type = st.sidebar.radio("选择抢筹类型", ("早盘抢筹", "尾盘抢筹"), index=0)
race_type_code = "open" if race_type == "早盘抢筹" else "end"

# 日期选择（默认今天）
default_date = datetime.now().strftime("%Y%m%d")
date_str = st.sidebar.text_input("查询日期（格式：YYYYMMDD，空为当天）", value=default_date)

# 排序设置
st.sidebar.markdown("---")
st.sidebar.subheader("排序设置")
sort_options = {
    "抢筹委托金额": "抢筹委托金额",
    "抢筹成交金额": "抢筹成交金额",
    "抢筹幅度": "抢筹幅度",
    "抢筹占比": "抢筹占比",
    "涨跌幅": "涨跌幅"
}
sort_by = st.sidebar.selectbox("排序依据", list(sort_options.keys()), index=0)
sort_ascending = st.sidebar.checkbox("升序排列", value=False)

# 获取最新数据按钮
if st.sidebar.button("获取最新数据", type="primary"):
    st.cache_data.clear()

# --- 数据加载与处理 ---
with st.spinner("正在加载数据，请稍候..."):
    df = get_chip_race_data(race_type_code, date_str)

if df.empty:
    st.info("未获取到有效数据，请检查日期格式或尝试其他日期")
    st.stop()

# 数据排序
df_sorted = df.sort_values(by=sort_options[sort_by], ascending=sort_ascending)

# --- 数据可视化 ---
st.subheader(f"{race_type}数据可视化")

# 散点图：抢筹幅度 vs 涨跌幅，大小表示抢筹成交金额
fig = px.scatter(
    df_sorted,
    x="抢筹幅度",
    y="涨跌幅",
    size="抢筹成交金额",
    color="抢筹占比",
    hover_data=["代码", "名称", "最新价", "抢筹委托金额"],
    color_continuous_scale="RdYlGn",
    title=f"{race_type}：抢筹幅度 vs 涨跌幅（点大小表示抢筹成交金额）",
    labels={
        "抢筹幅度": "抢筹幅度(%)",
        "涨跌幅": "涨跌幅(%)",
        "抢筹占比": "抢筹占比(%)"
    }
)
fig.update_layout(
    xaxis_title="抢筹幅度(%)",
    yaxis_title="涨跌幅(%)",
    height=600
)
st.plotly_chart(fig, use_container_width=True)

# 前10名抢筹金额柱状图
top10_amount = df_sorted.nlargest(10, "抢筹成交金额")
fig2 = px.bar(
    top10_amount,
    x="名称",
    y="抢筹成交金额",
    color="抢筹占比",
    color_continuous_scale="Viridis",
    title=f"{race_type}：抢筹成交金额前10名",
    hover_data=["代码", "抢筹占比", "涨跌幅"]
)
fig2.update_layout(
    xaxis_title="股票名称",
    yaxis_title="抢筹成交金额",
    height=500
)
st.plotly_chart(fig2, use_container_width=True)

# --- 数据表格展示 ---
st.subheader(f"{race_type}详细数据")
st.dataframe(df_sorted, use_container_width=True)

# 数据导出功能
st.subheader("数据导出")
csv = df_sorted.to_csv(index=False, encoding="utf-8-sig")
st.download_button(
    label="下载数据为CSV",
    data=csv,
    file_name=f"{race_type}_{date_str}.csv",
    mime="text/csv",
)