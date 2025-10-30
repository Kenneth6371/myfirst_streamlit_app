import streamlit as st
import pandas as pd
import numpy as np
import pywencai as wc
from datetime import datetime, timedelta
import time
# 设置页面标题和说明
st.set_page_config(page_title="市场风格统计分析", layout="wide")
st.title("📈 市场风格统计分析")
st.markdown("""
**市场风格分析** - 本应用提供手动刷新功能，统计:
- **按市值分类**: 大盘股(>1000亿)、中盘股(100-1000亿)、小盘股(20-100亿)、微盘股(<20亿)的上涨比例
- **按股价分类**: 高价股(≥100元)、中价股(10-100元)、低价股(<10元)的上涨比例  
- **按市场板块**: 上证、深证、创业板、科创板、北交所的上涨幅度
""")
# 使用session_state存储数据，避免重复获取
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = pd.DataFrame()
if 'last_update' not in st.session_state:
    st.session_state.last_update = "尚未更新"
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'first_load' not in st.session_state:
    st.session_state.first_load = True  # 首次加载标志
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.now().date()  # 默认今天
# 添加缓存装饰器
@st.cache_data(ttl=300, show_spinner="正在获取股票数据...")  # 5分钟缓存
def get_stock_data_cached(query_date):
    """
    使用pywencai获取股票数据（带缓存功能）
    使用通配符获取指定日期的数据
    """
    try:
        # 将日期格式化为字符串，用于查询
        date_str = query_date.strftime("%Y-%m-%d")
        # 构建查询语句，使用通配符获取指定日期的数据[6,8](@ref)
        # 通配符是一种可以匹配符合一定规则的字符串的特殊字符
        query = f"{date_str} 股票涨跌 市值， 涨跌幅"
        # 获取股票数据，包含涨跌幅、市值等信息
        res = wc.get(
            question=query,
            query_type="stock",
            loop=True  # 启用自动翻页获取更多数据
        )
        if res is not None and not res.empty:
            # 添加数据日期列
            res['数据日期'] = query_date
            st.success(f"成功获取 {len(res)} 条{date_str}的股票数据")
            return res
        else:
            st.warning(f"获取{date_str}的数据为空，请检查查询条件")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"获取股票数据时出错: {str(e)}")
        return pd.DataFrame()
@st.cache_data(ttl=300)  # 5分钟缓存
def categorize_stocks_cached(df):
    """
    对股票数据进行分类统计（带缓存功能）
    """
    if df.empty:
        return None
    results = {}
    # 智能查找市值字段
    market_cap_col = find_market_cap_column(df)
    if market_cap_col is None:
        st.error("无法找到市值字段，请检查数据源")
        return None
    # 重命名市值列为统一名称以便后续处理
    df.rename(columns={market_cap_col: '总市值'}, inplace=True)
    # 确保数据类型正确
    df['总市值'] = pd.to_numeric(df['总市值'], errors='coerce')
    # 查找涨跌幅字段
    change_col = None
    for col in df.columns:
        if '涨跌幅' in str(col):
            change_col = col
            break
    if change_col is None:
        st.error("无法找到涨跌幅字段")
        return None
    df['涨跌幅'] = pd.to_numeric(df[change_col], errors='coerce')
    # 查找价格字段
    price_col = None
    for col in df.columns:
        if any(word in str(col) for word in ['最新价', '收盘价', '价格', '股价']):
            price_col = col
            break
    if price_col:
        df['最新价'] = pd.to_numeric(df[price_col], errors='coerce')
    else:
        st.warning("无法找到价格字段，股价分类将不可用")
    # 过滤掉无效数据
    df = df.dropna(subset=['总市值', '涨跌幅'])
    # 1. 按市值分类统计
    market_cap_bins = [0, 20e8, 100e8, 1000e8, float('inf')]  # 转换为元单位
    market_cap_labels = ['微盘股(<20亿)', '小盘股(20-100亿)', '中盘股(100-1000亿)', '大盘股(>1000亿)']
    df['市值分类'] = pd.cut(df['总市值'], bins=market_cap_bins, labels=market_cap_labels, right=False)
    cap_stats = {}
    for category in market_cap_labels:
        category_df = df[df['市值分类'] == category]
        if not category_df.empty:
            rise_ratio = len(category_df[category_df['涨跌幅'] > 0]) / len(category_df)
            cap_stats[category] = {
                '总数': len(category_df),
                '上涨数量': len(category_df[category_df['涨跌幅'] > 0]),
                '上涨比例': rise_ratio,
                '平均涨跌幅': category_df['涨跌幅'].mean()
            }
    results['市值分类'] = cap_stats
    # 2. 按股价高低分类统计 - 修改为三类：低价股(<10元)、中价股(10-100元)、高价股(≥100元)
    if '最新价' in df.columns:
        # 使用np.select进行多条件分类
        conditions = [
            df['最新价'] < 10,
            (df['最新价'] >= 10) & (df['最新价'] < 100),
            df['最新价'] >= 100
        ]
        choices = ['低价股(<10元)', '中价股(10-100元)', '高价股(≥100元)']
        df['股价分类'] = np.select(conditions, choices, default='未知')
        price_stats = {}
        for category in choices:
            category_df = df[df['股价分类'] == category]
            if not category_df.empty:
                rise_ratio = len(category_df[category_df['涨跌幅'] > 0]) / len(category_df)
                price_stats[category] = {
                    '总数': len(category_df),
                    '上涨数量': len(category_df[category_df['涨跌幅'] > 0]),
                    '上涨比例': rise_ratio,
                    '平均涨跌幅': category_df['涨跌幅'].mean()
                }
        results['股价分类'] = price_stats
    # 3. 按市场板块分类统计
    board_stats = {}
    # 尝试根据股票代码前缀判断板块
    # 确保股票代码是字符串类型
    df['股票代码'] = df['股票代码'].astype(str)
    df['板块'] = df['股票代码'].apply(lambda x:
                                      '上证' if x.startswith('6') else
                                      '深证' if x.startswith('0') else
                                      '创业板' if x.startswith('3') else
                                      '科创板' if x.startswith('688') else
                                      '北交所' if x.startswith('8') else '其他')
    for board in ['上证', '深证', '创业板', '科创板', '北交所']:
        board_df = df[df['板块'] == board]
        if not board_df.empty:
            rise_ratio = len(board_df[board_df['涨跌幅'] > 0]) / len(board_df)
            board_stats[board] = {
                '总数': len(board_df),
                '上涨数量': len(board_df[board_df['涨跌幅'] > 0]),
                '上涨比例': rise_ratio,
                '平均涨跌幅': board_df['涨跌幅'].mean()
            }
    results['板块分类'] = board_stats
    return results
def find_market_cap_column(df):
    """
    智能查找市值字段：优先寻找'总市值'，如果没有则查找包含'总市值'字样的列
    """
    # 优先寻找精确匹配
    if '总市值' in df.columns:
        return '总市值'
    # 查找包含"总市值"字样的列
    market_cap_cols = [col for col in df.columns if '总市值' in str(col)]
    if market_cap_cols:
        return market_cap_cols[0]  # 返回第一个匹配的列
    # 如果还是没有找到，尝试其他常见的市值字段名称
    alternative_cols = [col for col in df.columns if any(word in str(col) for word in ['市值', 'marketcap', 'MKTCAP'])]
    if alternative_cols:
        return alternative_cols[0]
    # 如果完全找不到，返回None
    return None
def update_data():
    """
    更新数据函数
    """
    with st.spinner('正在获取最新数据...'):
        # 清除缓存以确保获取最新数据
        st.cache_data.clear()
        df = get_stock_data_cached(st.session_state.selected_date)
        if not df.empty:
            results = categorize_stocks_cached(df)
            if results:
                st.session_state.results = results
                st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.stock_data = df
                st.session_state.first_load = False  # 首次加载完成
                st.success("数据更新完成!")
            else:
                st.warning("数据分类统计失败")
        else:
            st.warning("未获取到有效股票数据")
# 在侧边栏添加日期选择和刷新按钮
with st.sidebar:
    st.header("控制面板")
    # 日期选择器[5](@ref)
    selected_date = st.date_input(
        "选择数据日期",
        value=datetime.now().date(),
        max_value=datetime.now().date(),
        help="选择要获取数据的日期"
    )
    # 更新session_state中的日期
    st.session_state.selected_date = selected_date
    if st.button("🔄 获取数据", type="primary"):
        update_data()
    st.info("""
    **使用说明:**
    - 选择日期后点击"获取数据"按钮
    - 数据每5分钟自动缓存一次
    - 支持获取历史日期数据
    - 分类统计包括市值、股价和板块
    """)
# 显示最后更新时间和数据日期
st.info(f"最后更新时间: {st.session_state.last_update} | 数据日期: {st.session_state.selected_date}")
# 首次自动加载数据
if st.session_state.first_load:
    update_data()
# 显示统计结果
if st.session_state.results:
    # 显示数据日期信息
    st.subheader(f"{st.session_state.selected_date} 市场风格分析")
    # 创建三列布局
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("📊 市值分类统计")
        if '市值分类' in st.session_state.results:
            cap_data = st.session_state.results['市值分类']
            cap_df = pd.DataFrame.from_dict(cap_data, orient='index')
            st.dataframe(cap_df.style.format({
                '上涨比例': '{:.2%}',
                '平均涨跌幅': '{:.2f}%'
            }), use_container_width=True)
        else:
            st.warning("暂无市值分类数据")
    with col2:
        st.subheader("💵 股价分类统计")
        if '股价分类' in st.session_state.results:
            price_data = st.session_state.results['股价分类']
            price_df = pd.DataFrame.from_dict(price_data, orient='index')
            st.dataframe(price_df.style.format({
                '上涨比例': '{:.2%}',
                '平均涨跌幅': '{:.2f}%'
            }), use_container_width=True)
        else:
            st.warning("暂无股价分类数据")
    with col3:
        st.subheader("🏛️ 板块分类统计")
        if '板块分类' in st.session_state.results:
            board_data = st.session_state.results['板块分类']
            board_df = pd.DataFrame.from_dict(board_data, orient='index')
            st.dataframe(board_df.style.format({
                '上涨比例': '{:.2%}',
                '平均涨跌幅': '{:.2f}%'
            }), use_container_width=True)
        else:
            st.warning("暂无板块分类数据")
else:
    if not st.session_state.first_load:
        st.info("请选择日期并点击'获取数据'按钮获取数据")