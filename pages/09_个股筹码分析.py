import streamlit as st
import akshare as ak
import pandas as pd

# 设置页面配置
st.set_page_config(layout="wide", page_title="股票筹码分布查询")
st.title("股票筹码分布数据")
st.markdown("数据来源：东方财富网 (通过 akshare 获取)")

# 数据获取函数（带缓存，避免重复请求）
@st.cache_data(ttl=300)  # 缓存5分钟
def get_stock_cyq_data(symbol: str = "000001"):
    try:
        # 调用akshare接口获取筹码分布数据
        df = ak.stock_cyq_em(symbol=symbol, adjust="")
        # 简单数据清洗：处理可能的空值
        if not df.empty:
            df = df.dropna(how="all")
        return df
    except Exception as e:
        st.error(f"数据获取失败: {str(e)}")
        return pd.DataFrame()

# 侧边栏控件
st.sidebar.header("查询设置")
# 股票代码输入框，默认000001
stock_symbol = st.sidebar.text_input(
    "请输入股票代码",
    value="000001",
    help="例如：000001（平安银行）、600036（招商银行）"
)
# 刷新数据按钮
if st.sidebar.button("获取最新数据", type="primary"):
    st.cache_data.clear()
    st.success("缓存已清除，将加载最新数据")

# 数据加载与显示
with st.spinner("正在加载数据，请稍候..."):
    cyq_df = get_stock_cyq_data(symbol=stock_symbol)

if cyq_df.empty:
    st.warning("未获取到有效数据，请检查股票代码是否正确或稍后重试")
else:
    st.subheader(f"股票 {stock_symbol} 筹码分布数据")
    # 显示数据表格
    st.dataframe(cyq_df, use_container_width=True)
    
    # 提供数据下载功能
    csv_data = cyq_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="下载数据为CSV",
        data=csv_data,
        file_name=f"{stock_symbol}_筹码分布数据.csv",
        mime="text/csv"
    )

# 显示数据说明
st.markdown("""
### 数据说明
- 筹码分布数据展示了不同价格区间的筹码占比情况
- 数据周期：根据接口返回的默认周期（通常包含近期交易日数据）
- 调整参数：当前使用默认调整方式（adjust=""），如需复权数据可修改参数
""")
