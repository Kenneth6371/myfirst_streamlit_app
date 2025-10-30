
import streamlit as st
import pywencai
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import akshare as ak
# 设置全局显示选项
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_colwidth', 100)
# 数据获取函数（带缓存优化）
@st.cache_data(ttl=3600, show_spinner=False)
def get_high_stock_data(selected_date):
    """根据选定日期获取创新高个股数据"""
    query_date = selected_date.strftime("%Y%m%d")
    query = f"{query_date}创新高个股，所属同花顺二级行业,流通市值"
    return pywencai.get(query=query, query_type="stock", sort_order='desc', loop=True)
# 主应用
def app():
    st.title("📈 创新高个股行业分布分析")
    # 日期选择器
    selected_date = st.date_input(
        "选择分析日期",
        value=datetime.now(),
        min_value=datetime(2020, 1, 1),
        max_value=datetime.now()
    )
    prev_date = selected_date - timedelta(days=1)
    # 数据获取与预处理
    with st.spinner(f"正在获取{selected_date.strftime('%Y-%m-%d')}及前一日数据..."):
        try:
            # 获取当日数据
            df_today = get_high_stock_data(selected_date)
            #print(df_today.head(1))
            # 获取今天的日期并格式化为 YYYYMMDD
            today = datetime.now().date()
            trade_date_range = get_trade_dates()
            if trade_date_range.empty:
                st.error("无法获取交易日数据，请检查网络连接或稍后再试。")
                return
            if not trade_date_range.empty:
                if today in trade_date_range['trade_date'].values:
                    default_date = today
                else:
                    default_date = trade_date_range[trade_date_range['trade_date'] <= today]['trade_date'].max()
            else:
                default_date = today
            try:
                # 查找包含"总市值"的列
                market_value_col = None
                for col in df_today.columns:
                    if '总市值' in col:
                        market_value_col = col
                        break
                if market_value_col:
                    # 如果找到了总市值列
                    df_today = df_today.rename(columns={
                        '股票代码': 'symbol',
                        '股票简称': 'name',
                        '所属同花顺二级行业': 'industry',
                        market_value_col: 'shizhi',
                        '最新价': 'price',
                        '最新涨跌幅': 'change_percent',
                        '所属概念': 'gainian'
                    })[['symbol', 'name', 'industry', 'shizhi', 'gainian', 'price', 'change_percent']]
                else:
                    # 如果没有找到总市值列，创建空列
                    st.warning("未找到总市值数据，市值列将显示为空")
                    df_today = df_today.rename(columns={
                        '股票代码': 'symbol',
                        '股票简称': 'name',
                        '所属同花顺二级行业': 'industry',
                        '最新价': 'price',
                        '最新涨跌幅': 'change_percent',
                        '所属概念': 'gainian'
                    })
                    df_today['shizhi'] = None
                    df_today = df_today[['symbol', 'name', 'industry', 'shizhi', 'gainian', 'price', 'change_percent']]
            except Exception as e:
                # 其他列名也可能变化，使用更通用的处理方式
                st.warning(f"列名匹配异常")
            # 获取前一日数据
            df_prev = get_high_stock_data(prev_date)
            df_prev = df_prev.rename(columns={
                '股票代码': 'symbol',
                '股票简称': 'name',
                '所属同花顺二级行业': 'industry',
                '最新价': 'price',
                '最新涨跌幅': 'change_percent'
            })[['symbol', 'name', 'industry']]
            # 创建前一日个股集合
            prev_high_symbols = set(df_prev['symbol'])
            # 添加连续创新高标记列
            df_today['连续创新高'] = df_today['symbol'].apply(
                lambda x: '✅' if x in prev_high_symbols else '➖'
            )
            # =====================================================
            # 行业增长统计
            industry_stats_today = (
                df_today.groupby('industry')
                .agg(count_today=('symbol', 'size'))
                .reset_index()
            )
            industry_stats_prev = (
                df_prev.groupby('industry')
                .agg(count_prev=('symbol', 'size'))
                .reset_index()
            )
            # 合并两日数据计算增长量
            industry_stats = pd.merge(
                industry_stats_today,
                industry_stats_prev,
                on='industry',
                how='left'
            ).fillna(0)
            industry_stats['growth'] = industry_stats['count_today'] - industry_stats['count_prev']
            industry_stats['growth_rate'] = (industry_stats['growth'] / industry_stats['count_prev'].replace(0,
                                                                                                             1)) * 100
            industry_stats = industry_stats.sort_values('count_today', ascending=False)
            df_today['shizhi'] = pd.to_numeric(df_today['shizhi']/100000000, errors='coerce')
            # 数据类型转换
            df_today['price'] = pd.to_numeric(df_today['price'], errors='coerce')
            df_today['change_percent'] = pd.to_numeric(
                df_today['change_percent'].str.replace('%', ''),
                errors='coerce'
            )
            # ==================== 布局设计 ====================
            st.subheader(f"创新高个股列表 (共{len(df_today)}只)")
            st.dataframe(
                df_today.sort_values('change_percent', ascending=False),
                height=500,
                column_config={
                    "symbol": "代码",
                    "name": "名称",
                    "industry": st.column_config.Column("行业", width="medium"),
                    'shizhi':'总市值',
                    "price": st.column_config.NumberColumn("价格", format="%.2f"),
                    "change_percent": st.column_config.NumberColumn("涨幅%", format="%.1f"),
                    'gainian':'概念',
                    "连续创新高": st.column_config.Column(
                        "连续创新高",
                        help="✅表示连续两日创新高，➖表示今日首次创新高"
                    )
                }
            )
            # =====================================================
            # 行业分布TOP10图表
            st.subheader("行业分布TOP10")
            top_industries = industry_stats.head(10).sort_values('count_today', ascending=True)
            fig1 = px.bar(
                top_industries,
                x='count_today',
                y='industry',
                orientation='h',
                labels={'count_today': '创新高数量', 'industry': ''},
                text_auto=True,
                color='growth',
                color_continuous_scale=px.colors.diverging.RdYlGn,
                color_continuous_midpoint=0
            )
            # 添加增长量标注
            for i, row in enumerate(top_industries.itertuples()):
                growth_text = f"+{row.growth}" if row.growth > 0 else str(row.growth)
                fig1.add_annotation(
                    x=row.count_today + 1,
                    y=row.industry,
                    text=growth_text,
                    showarrow=False,
                    font=dict(color='green' if row.growth > 0 else 'red')
                )
            st.plotly_chart(fig1, use_container_width=True)
            # ==================== 交互式筛选功能 ====================
            st.divider()
            st.subheader("🔍 行业筛选分析")
            selected_industries = st.multiselect(
                "选择行业：",
                options=industry_stats['industry'].tolist(),
                default=industry_stats.head(10)['industry'].tolist()
            )
            if selected_industries:
                filtered_df = df_today[df_today['industry'].isin(selected_industries)]
                for industry in selected_industries:
                    industry_df = filtered_df[filtered_df['industry'] == industry]
                    industry_growth = industry_stats[industry_stats['industry'] == industry].iloc[0]
                    with st.expander(
                            f"{industry} - {len(industry_df)}只个股 (较前日: {industry_growth['growth']:+}只)"):
                        st.dataframe(
                            industry_df,
                            hide_index=True,
                            column_config={
                                "symbol": "代码",
                                "name": "名称",
                                'industry':"行业",
                                "shizhi":"总市值",
                                "price": st.column_config.NumberColumn("价格", format="%.2f"),
                                "change_percent": st.column_config.NumberColumn("涨幅%", format="%.1f"),
                                'gainian': '概念',
                                "连续创新高": st.column_config.Column("连续创新高")
                            }
                        )
        except Exception as e:
            st.error(f"数据获取失败: {str(e)}")
            st.info("⚠️ 可能原因：1. 所选日期非交易日 2. 数据源无当日记录")
    # 底部元数据
    st.caption(f"数据更新于: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据来源: 同花顺")
@st.cache_data(ttl=86400)
def get_trade_dates():
    try:
        trade_date_range = ak.tool_trade_date_hist_sina()
        trade_date_range['trade_date'] = pd.to_datetime(trade_date_range['trade_date']).dt.date
        return trade_date_range
    except Exception as e:
        st.error(f"获取交易日数据时出错: {str(e)}")
        return pd.DataFrame()
if __name__ == "__main__":
    # 设置页面布局
    #st.set_page_config(page_title="创新高个股行业分析", layout="wide", page_icon="📈")
    app()