
import akshare as ak
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import random
# 设置页面配置
st.set_page_config(
    page_title="国庆节行情分析",
    page_icon="🇨🇳",
    layout="wide"
)
# 应用标题
st.title("🇨🇳 近10年国庆节前后行情统计分析")
st.markdown("""
本应用分析**近10年国庆节前后**的市场表现，包括：
- **国庆节前1天** → **国庆节后第1天**的涨跌幅
- **国庆节前1天** → **国庆节后第1周**的涨跌幅
""")
# 侧边栏配置
st.sidebar.header("分析参数设置")
start_year = st.sidebar.selectbox("起始年份", range(2014, 2024), index=0)
end_year = st.sidebar.selectbox("结束年份", range(2015, 2026), index=10)
index_code = st.sidebar.selectbox("选择指数",
                                  ["000001", "000300", "000905", "000852"],
                                  format_func=lambda x: {
                                      "000001": "上证指数",
                                      "000300": "沪深300",
                                      "000905": "中证500",
                                      "000852": "中证1000"
                                  }[x])
@st.cache_data(ttl=3600)
def get_index_data(symbol, start_year, end_year):
    """获取指数历史数据（修复列名问题）"""
    try:
        # 添加请求间隔，避免被服务器限制
        time.sleep(random.uniform(2, 4))
        # 使用更稳定的接口获取数据
        df = ak.stock_zh_index_daily(symbol=symbol)
        # 检查数据是否为空
        if df.empty:
            st.error(f"获取到的数据为空，请检查指数代码 {symbol} 是否正确")
            return pd.DataFrame()
        # 统一列名处理：检查可能的列名变体
        column_mapping = {}
        for col in df.columns:
            if 'date' in col.lower() or '日期' in col or 'trade_date' in col:
                column_mapping[col] = 'date'
            elif 'close' in col.lower() or '收盘' in col:
                column_mapping[col] = 'close'
        # 重命名列
        df = df.rename(columns=column_mapping)
        # 确保必要的列存在
        if 'date' not in df.columns or 'close' not in df.columns:
            st.error(f"数据列不完整，现有列: {df.columns.tolist()}")
            return pd.DataFrame()
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        # 过滤日期范围
        start_date = f'{start_year}-01-01'
        end_date = f'{end_year}-12-31'
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        if df.empty:
            st.error(f"在指定时间范围 {start_date} 到 {end_date} 内没有找到数据")
            return pd.DataFrame()
        df = df.sort_values('date')
        return df[['date', 'close']]
    except Exception as e:
        st.error(f"数据获取失败: {e}")
        return pd.DataFrame()
def find_trading_dates(df, target_date):
    """在数据框中查找目标日期附近的交易日"""
    if df.empty:
        return None, None
    # 查找目标日期之前的最后一个交易日
    pre_dates = df[df['date'] <= target_date]
    if len(pre_dates) > 0:
        pre_date = pre_dates.iloc[-1]
    else:
        return None, None
    # 查找目标日期之后的第一个交易日
    post_dates = df[df['date'] > target_date]
    if len(post_dates) > 0:
        post_date = post_dates.iloc[0]
    else:
        return pre_date, None
    return pre_date, post_date
def calculate_national_day_returns(df, start_year, end_year):
    """计算国庆节前后收益率"""
    results = []
    for year in range(start_year, end_year + 1):
        try:
            # 国庆节日期（10月1日）
            national_day = datetime(year, 10, 1)
            # 找到节前最后一个交易日（9月30日或之前）
            pre_date_data, _ = find_trading_dates(df, national_day - timedelta(days=1))
            if pre_date_data is None:
                st.warning(f"未找到{year}年国庆节前的交易日数据")
                continue
            # 找到节后第一个交易日（10月8日或之后）
            _, post_day1_data = find_trading_dates(df, national_day + timedelta(days=7))
            if post_day1_data is None:
                st.warning(f"未找到{year}年国庆节后的首个交易日数据")
                continue
            # 找到节后一周的交易日（约5个交易日后）
            post_week_data = None
            post_dates_after = df[df['date'] > post_day1_data['date']]
            if len(post_dates_after) >= 5:
                post_week_data = post_dates_after.iloc[4]  # 第5个交易日
            elif len(post_dates_after) > 0:
                post_week_data = post_dates_after.iloc[-1]  # 最后一个可用交易日
            else:
                post_week_data = post_day1_data  # 如果没有后续数据，使用节后首日
            # 计算涨跌幅
            pre_close = pre_date_data['close']
            post_day1_close = post_day1_data['close']
            post_week_close = post_week_data['close']
            day1_return = (post_day1_close / pre_close - 1) * 100
            week1_return = (post_week_close / pre_close - 1) * 100
            results.append({
                '年份': year,
                '节前日期': pre_date_data['date'].strftime('%Y-%m-%d'),
                '节前收盘价': round(pre_close, 2),
                '节后首日日期': post_day1_data['date'].strftime('%Y-%m-%d'),
                '节后首日收盘价': round(post_day1_close, 2),
                '节后一周日期': post_week_data['date'].strftime('%Y-%m-%d'),
                '节后一周收盘价': round(post_week_close, 2),
                '后1日涨跌幅%': round(day1_return, 2),
                '后1周涨跌幅%': round(week1_return, 2)
            })
        except Exception as e:
            st.warning(f"处理{year}年数据时出错: {e}")
            continue
    return pd.DataFrame(results)
# 主程序
def app():
    # 显示加载状态
    with st.spinner('正在加载指数数据...'):
        df = get_index_data(f"sh{index_code}", start_year, end_year)
    # 计算国庆节收益率
    with st.spinner('正在计算国庆节前后收益率...'):
        results_df = calculate_national_day_returns(df, start_year, end_year)
    if results_df.empty:
        st.error("未能计算出有效的收益率数据。")
        return
    # 显示关键统计指标
    st.subheader("📊 关键统计指标")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_day1 = results_df['后1日涨跌幅%'].mean()
        st.metric("后1日平均涨跌幅", f"{avg_day1:.2f}%")
    with col2:
        avg_week1 = results_df['后1周涨跌幅%'].mean()
        st.metric("后1周平均涨跌幅", f"{avg_week1:.2f}%")
    with col3:
        positive_day1_prob = (results_df['后1日涨跌幅%'] > 0).mean() * 100
        st.metric("节后首日上涨概率", f"{positive_day1_prob:.1f}%")
    with col4:
        positive_week1_prob = (results_df['后1周涨跌幅%'] > 0).mean() * 100
        st.metric("节后一周上涨概率", f"{positive_week1_prob:.1f}%")
    # 可视化图表
    st.subheader("📈 国庆节前后涨跌幅可视化")
    # 1. 年度涨跌幅柱状图
    if not results_df.empty:
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            name='后1日涨跌幅',
            x=results_df['年份'],
            y=results_df['后1日涨跌幅%'],
            marker_color='#1f77b4'
        ))
        fig1.add_trace(go.Bar(
            name='后1周涨跌幅',
            x=results_df['年份'],
            y=results_df['后1周涨跌幅%'],
            marker_color='#ff7f0e'
        ))
        fig1.update_layout(
            title="国庆节前后涨跌幅年度对比",
            xaxis_title="年份",
            yaxis_title="涨跌幅 (%)",
            barmode='group',
            height=400
        )
        st.plotly_chart(fig1, use_container_width=True)
    # 详细数据表格
    st.subheader("📋 详细数据表格")
    if not results_df.empty:
        st.dataframe(results_df, use_container_width=True)
        # 统计摘要
        st.subheader("📊 详细统计摘要")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**后1日涨跌幅统计**")
            day1_stats = results_df['后1日涨跌幅%'].describe()
            st.write(f"- **平均值**: {day1_stats['mean']:.2f}%")
            st.write(f"- **标准差**: {day1_stats['std']:.2f}%")
            if len(results_df) > 0:
                st.write(
                    f"- **最大值**: {day1_stats['max']:.2f}% ({results_df.loc[results_df['后1日涨跌幅%'].idxmax(), '年份']}年)")
                st.write(
                    f"- **最小值**: {day1_stats['min']:.2f}% ({results_df.loc[results_df['后1日涨跌幅%'].idxmin(), '年份']}年)")
        with col2:
            st.write("**后1周涨跌幅统计**")
            week1_stats = results_df['后1周涨跌幅%'].describe()
            st.write(f"- **平均值**: {week1_stats['mean']:.2f}%")
            st.write(f"- **标准差**: {week1_stats['std']:.2f}%")
            if len(results_df) > 0:
                st.write(
                    f"- **最大值**: {week1_stats['max']:.2f}% ({results_df.loc[results_df['后1周涨跌幅%'].idxmax(), '年份']}年)")
                st.write(
                    f"- **最小值**: {week1_stats['min']:.2f}% ({results_df.loc[results_df['后1周涨跌幅%'].idxmin(), '年份']}年)")
if __name__ == "__main__":
    app()