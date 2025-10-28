
import akshare as ak
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
def get_buffett_index():
    """通过AKShare获取实时巴菲特指标数据"""
    df = ak.stock_buffett_index_lg()
    #print(df)
    # 数据清洗与格式转换
    latest_data = df.iloc[-1].to_dict()  # 取最新一条数据
    return {
        'date': pd.to_datetime(latest_data['日期']).strftime('%Y-%m-%d'),
        'total_market': round(latest_data['总市值'] / 1e4, 2),  # 转换为万亿元
        'gdp': round(latest_data['GDP'] / 1e4, 2),  # 转换为万亿元
        'ratio': round(latest_data['总市值'] / latest_data['GDP'] * 100, 1),
        'decade_percentile': latest_data['近十年分位数'],
        'history_percentile': latest_data['总历史分位数']
    }
def get_sh_index():
    """获取上证指数历史数据（含最新交易日）"""
    df = ak.stock_zh_index_daily(symbol="sh000001")
    return df[['date', 'open', 'high', 'low', 'close', 'volume']]
def app():
    # 创建Streamlit界面
    st.title("A股巴菲特指标")
    current_data = get_buffett_index()
    df = get_sh_index().tail(200)
    # 指标分析模块
    with st.container():
        st.subheader(f"{current_data['date']} 数据")
        st.metric("巴菲特指标",
                  f"{current_data['ratio']}%",
                  help="总市值/GDP比率")
        st.write(f"总市值：{current_data['total_market']} 万亿元")
        st.write(f"GDP总量：{current_data['gdp']} 万亿元")
        # 动态进度条（根据历史分位数）
        progress_value = current_data['history_percentile'] * 100
        st.progress(progress_value / 100,
                    text=f"历史分位数：{progress_value:.1f}%")
        # 智能仓位建议
        if current_data['ratio'] < 60:
            st.success("建议仓位：100%（极度低估）")
        elif 60 <= current_data['ratio'] < 70:
            st.success("建议仓位：80%-100%（价值区间）")
        elif 70 <= current_data['ratio'] <= 80:
            ratio = 1 - (current_data['ratio'] - 70) / 10
            st.warning(f"建议仓位：{ratio * 100:.0f}%（合理区间）")
        else:
            st.error("建议仓位：<30%（高风险区域）")
        # 动态K线图（含最新数据）
        fig = go.Figure(data=[go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing_line_color='red',
            decreasing_line_color='green',
            name='上证指数'
        )])
        fig.update_layout(
            title='上证指数实时K线图',
            yaxis_title='点位',
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)

# 应用入口
if __name__ == "__main__":
    app()