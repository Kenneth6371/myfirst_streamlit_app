import streamlit as st
import requests
import pandas as pd
import json
import re
import time
from datetime import date, timedelta
import altair as alt # <--- 1. 导入 Altair 库

# --- 1. 页面配置 ---
st.set_page_config(
    layout="wide",
    page_title="融资融券查询",
    page_icon="📈"
)

# --- 2. 核心数据获取函数 (与上一版相同) ---
@st.cache_data(ttl=3600)
def get_sse_margin_data(stock_code: str, start_date: str, end_date: str):
    """
    获取上海证券交易所指定代码和日期范围的融资融券交易明细。
    """
    
    base_url = "https://query.sse.com.cn/commonSoaQuery.do"
    headers = {
        "Referer": "http://www.sse.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
    }
    params = {
        "jsonCallBack": f"jsonpCallback{int(time.time() * 1000)}",
        "isPagination": "true",
        "pageHelp.pageSize": 500,
        "pageHelp.pageNo": 1,
        "sqlId": "RZRQ_MX_INFO",
        "preStockCode": stock_code,
        "beginDate": start_date,
        "endDate": end_date,
        "_": int(time.time() * 1000)
    }

    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status() 

        jsonp_text = response.text
        match = re.search(r'^\w+\((.*)\)$', jsonp_text)
        
        if not match:
            st.error(f"错误: 无法解析JSONP响应。原始响应: {jsonp_text[:200]}...")
            return None

        json_str = match.group(1)
        data = json.loads(json_str)

        if data.get('actionErrors') or not data.get('result'):
            st.warning(f"接口未返回数据: {data.get('actionErrors', '未找到 result 数据')}")
            return None

        df = pd.DataFrame(data['result'])
        
        if 'opDate' in df.columns:
            df['opDate'] = pd.to_datetime(df['opDate'], format='%Y%m%d')

        column_map = {
            "opDate": "信用交易日期",
            "securityCode": "标的证券代码",
            "securityAbbr": "标的证券简称",
            "rzye": "融资余额(元)",
            "rzmre": "融资买入额(元)",
            "rzche": "融资偿还额(元)",
            "rqyl": "融券余量",
            "rqmcl": "融券卖出量",
            "rqchl": "融券偿还量"
        }
        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

        numeric_cols_cn = ['融资余额(元)', '融资买入额(元)', '融资偿还额(元)', 
                           '融券余量', '融券卖出量', '融券偿还量']
        
        for col in numeric_cols_cn:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', ''), 
                    errors='coerce'
                )
        
        if "信用交易日期" in df.columns:
             df = df.sort_values(by="信用交易日期")
        
        display_cols = ['信用交易日期', '标的证券代码', '标的证券简称', 
                        '融资余额(元)', '融资买入额(元)', '融资偿还额(元)',
                        '融券余量', '融券卖出量', '融券偿还量']
        
        final_cols = [col for col in display_cols if col in df.columns]
        
        return df[final_cols]

    except requests.exceptions.RequestException as e:
        st.error(f"HTTP 请求失败: {e}")
        return None
    except Exception as e:
        st.error(f"处理数据时发生错误: {e}")
        return None

# --- 3. Streamlit 页面布局 ---

st.title("📈 融资融券交易明细查询")
st.caption("数据来源：上海证券交易所 (SSE)")

# --- 4. 侧边栏输入 ---
st.sidebar.header("查询条件")
stock_code = st.sidebar.text_input("证券代码 (如: 600030)", "600030")

# 默认日期
default_end = date(2025, 11, 2)
default_start = date(2025, 10, 3)

date_range = st.sidebar.date_input(
    "选择日期范围",
    value=[default_start, default_end],
    help="选择开始日期和结束日期"
)
query_button = st.sidebar.button("开始查询")

# --- 5. 主页面逻辑 ---
if query_button:
    if len(date_range) != 2:
        st.sidebar.error("请选择完整的日期范围（开始日期和结束日期）。")
    else:
        start_dt, end_dt = date_range
        start_str = start_dt.strftime("%Y%m%d")
        end_str = end_dt.strftime("%Y%m%d")
        
        with st.spinner(f"正在查询 {stock_code} 从 {start_str} 到 {end_str} 的数据..."):
            data_df = get_sse_margin_data(stock_code, start_str, end_str)

        if data_df is not None and not data_df.empty:
            
            stock_name = data_df['标的证券简称'].iloc[0]
            st.subheader(f"{stock_name} ({stock_code}) 融资融券详情")

            # 5.1 显示关键指标
            col1, col2, col3 = st.columns(3)
            try:
                # <--- 2. 修改指标：标签改为“亿元”，数值除以 10^8
                balance_yi = data_df['融资余额(元)'].iloc[-1] / 100_000_000
                col1.metric(
                    "最新融资余额 (亿元)", 
                    f"{balance_yi:,.2f}" # 保留两位小数
                )
                
                # <--- 3. 修改指标：标签改为“亿元”，数值除以 10^8
                buy_total_yi = data_df['融资买入额(元)'].sum() / 100_000_000
                col2.metric(
                    "期间融资买入总额 (亿元)", 
                    f"{buy_total_yi:,.2f}" # 保留两位小数
                )
                
                # (这个指标保持不变)
                col3.metric(
                    "期间融券卖出总量 (股)", 
                    f"{data_df['融券卖出量'].sum():,.0f}"
                )
            except Exception:
                st.warning("计算指标时出错，部分数据可能缺失。")

            st.divider()

            # 5.2 显示图表
            # <--- 4. 修改图表标题
            st.subheader("融资买入额(亿元) 趋势图")
            
            if "融资买入额(元)" in data_df.columns:
                # <--- 5. 为图表创建“亿元”列
                data_df["融资买入额(亿元)"] = data_df["融资买入额(元)"] / 100_000_000
                
                # <--- 6. 使用 st.altair_chart 替换 st.line_chart
                # 创建 Altair 图表
                chart = alt.Chart(data_df).mark_line(point=True).encode(
                    # X 轴：使用“信用交易日期”，并设置标题为“日期”
                    x=alt.X('信用交易日期', title='日期'),
                    
                    # Y 轴：使用我们新创建的“亿元”列
                    y=alt.Y('融资买入额(亿元)', title='融资买入额 (亿元)'),
                    
                    # 关键：定义鼠标悬停时显示的工具提示
                    tooltip=[
                        # 提示1：日期，并格式化
                        alt.Tooltip('信用交易日期', title='日期', format='%Y-%m-%d'),
                        # 提示2：亿元金额，格式化为带2位小数的数字
                        alt.Tooltip('融资买入额(亿元)', title='金额(亿元)', format=',.2f')
                    ]
                ).interactive() # 允许图表缩放和平移

                # 显示图表
                st.altair_chart(chart, use_container_width=True)

            else:
                st.info("数据中未包含“融资买入额(元)”列，无法绘制图表。")

            # 5.3 显示原始数据
            st.subheader(f"详细数据 (共 {len(data_df)} 条)")
            st.dataframe(data_df, use_container_width=True)

        else:
            st.error("查询失败或未返回任何数据，请检查证券代码或日期范围。")
else:
    st.info("请在左侧侧边栏输入查询条件，然后点击“开始查询”。")