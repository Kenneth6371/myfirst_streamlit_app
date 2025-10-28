import streamlit as st
import pywencai
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak
import re
# 设置中文显示
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
# 核心概念映射字典
core_concept_mapping = {
    '白酒': [r'白酒'],
    '食品': [r'食品', r'乳制品', r'调味品'],
    '银行': [r'银行', r'城商行', r'农商行'],
    '黄金': [r'黄金', r'贵金属', r'金矿'],
    '电力': [r'电力', r'电网', r'输配电'],
    '创新药': [r'创新药', r'生物制药', r'抗体药物', r'基因治疗', r'ADC药物'],
    '汽车': [r'汽车', r'乘用车', r'商用车'],
    '电池': [r'电池'],
    '储能':[r'储能'],
    'CPO': [r'CPO', r'共封装光学', r'光电共封装'],
    'PCB': [r'PCB'],
    '铜箔':[r'铜箔', r'PET'],
    '算力': [r'算力'],
    'peek':[r'peek'],
    '液冷': [r'液冷', r'散热', r'冷却'],
    '信创':[r'信创'],
    'DeepSeek':[r'DeepSeek'],
    '华为海思':[r'华为海思'],
    '消费电子': [r'消费电子'],
    '芯片': [r'芯片', r'半导体', r'集成电路', r'光刻机', r'EDA', r'封测', r'晶圆'],
    '旅游': [r'旅游', r'文旅', r'景区', r'酒店', r'免税', r'旅行社'],
    '券商': [r'券商', r'证券', r'经纪', r'投行', r'财富'],
    '保险': [r'保险', r'寿险', r'财险'],
    '机器人': [r'机器人', r'自动化设备'],
    '化工': [r'化工', r'化学制品', r'新材料', r'精细化工', r'特种化学品', r'聚氨酯', r'氟化工'],
    '基建': [r'基建', r'工程建设', r'路桥建设', r'水利工程', r'轨道交通', r'城市管网'],
    '房地产': [r'地产',  r'物业', r'保障房', r'REITs'],
    '光伏':[r'光伏'],
    '军工': [r'军工', r'航空航天', r'武器装备',  r'军民融合', r'卫星导航'],
    '低空经济':[r'低空经济'],
    '海洋经济':[r'海洋经济'],
    '核电':['核电', '核聚变'],
    '建筑': [r'建筑'],
    '油气': [r'石油', r'天然气'],
    '三胎': [r'三胎'],
    '农业':[r'农业', r'种植'],
    '人造肉': [r'人造肉'],
    '高铁':[r'高铁'],
    '新经济':[r'谷子经济',r'IP经济'],
    '稳定币':[r'移动支付', r'cips',r'稳定币'],
}
exclude_concepts = ['融资融券', '国企改革', '深股通', '沪股通', '同花顺出海50', '同花顺漂亮100', '同花顺新质50',
                    '高股息精选', '超级品牌', '证金持股', '同花顺果指数', '同花顺中特估100']
@st.cache_data(ttl=3600, show_spinner="正在加载股票数据...")
def fetch_zt_data(target_date_str):
    try:
        query = "{target_date_str}涨停,所属概念,所属同花顺一级行业,所属同花顺二级行业"
        return pywencai.get(
            query=query,
            sort_key=f'涨停封单额[{target_date_str}]',
            sort_order='desc',
            loop=True
        )
    except Exception as e:
        st.error(f"数据接口异常: {str(e)}")
        return pd.DataFrame()
def map_to_core_concepts(concept_str, primary_industry, secondary_industry):

    if not isinstance(concept_str, str):
        return ""
    matched_concepts = set()
    # 1. 首先检查同花顺二级行业是否在所属概念字符串中
    if isinstance(secondary_industry, str) and isinstance(concept_str, str):
        for industry in secondary_industry.split(';'):
            industry = industry.strip()  # 去除空格
            if industry and industry not in exclude_concepts:
                # 检查二级行业是否在概念字符串中
                if industry in concept_str:
                    matched_concepts.add(industry)
    # 2. 然后检查同花顺一级行业是否在所属概念字符串中
    if isinstance(primary_industry, str) and isinstance(concept_str, str):
        for industry in primary_industry.split(';'):
            industry = industry.strip()  # 去除空格
            if industry and industry not in exclude_concepts:
                # 检查一级行业是否在概念字符串中
                if industry in concept_str:
                    matched_concepts.add(industry)
    # 3. 如果行业都没有匹配到，则检查所属概念中的每个部分是否包含核心概念映射中的关键词
    if not matched_concepts:
        # 分割概念字符串并处理每个概念
        concepts = [c.strip() for c in concept_str.split(';') if c.strip()]
        for concept in concepts:
            # 跳过排除概念
            if concept in exclude_concepts:
                continue
            # 检查该概念是否匹配核心概念映射中的任何模式
            for core_concept, patterns in core_concept_mapping.items():
                for pattern in patterns:
                    # 使用正则表达式搜索，检查概念中是否包含模式
                    if re.search(pattern, concept):
                        matched_concepts.add(core_concept)
                        break  # 匹配到一个核心概念就跳出内层循环
                else:
                    continue
                break  # 匹配到一个核心概念就跳出外层循环
    return ";".join(sorted(matched_concepts))
def process_data(raw_df, target_date_str):
    """数据处理流程"""
    if raw_df.empty:
        return raw_df
    required_columns = {
        '股票代码': '代码',
        '股票简称': '名称',
        '所属概念': '概念',
        '所属同花顺一级行业': '一级行业',
        '所属同花顺二级行业': '二级行业'
    }
    processed_df = raw_df[list(required_columns.keys())].copy()
    processed_df.rename(columns=required_columns, inplace=True)
    # 使用优化后的概念映射函数
    processed_df['核心概念'] = processed_df.apply(
        lambda row: map_to_core_concepts(
            row['概念'],
            row['一级行业'],
            row['二级行业']
        ),
        axis=1
    )
    return processed_df
def get_trade_dates():
    """获取交易日数据并格式化为两种形式"""
    try:
        trade_date_range = ak.tool_trade_date_hist_sina()
        trade_date_range['trade_date'] = pd.to_datetime(trade_date_range['trade_date']).dt.date
        trade_date_range['trade_date_str'] = trade_date_range['trade_date'].apply(
            lambda x: x.strftime('%Y%m%d'))
        return trade_date_range
    except Exception as e:
        st.error(f"获取交易日数据时出错: {str(e)}")
        return pd.DataFrame()
def app():
    # 设置页面配置
    st.set_page_config(page_title="涨停分析看板", layout="wide")
    with st.spinner("正在加载交易日数据..."):
        trade_date_df = get_trade_dates()
        if trade_date_df.empty:
            st.error("无法获取交易日数据，请检查网络连接或稍后再试。")
            return
    # 日期处理逻辑
    trade_dates = trade_date_df['trade_date'].tolist()
    today = datetime.now().date()
    # 计算默认日期
    if trade_dates:
        if today in trade_dates:
            default_date = today
        else:
            past_dates = [d for d in trade_dates if d <= today]
            default_date = max(past_dates) if past_dates else trade_dates[-1]
    else:
        default_date = today - timedelta(days=1)
    # 日期选择组件
    selected_date = st.date_input(
        "📅 选择分析日期",
        value=default_date,
        min_value=trade_dates[0] if trade_dates else today - timedelta(days=30),
        max_value=trade_dates[-1] if trade_dates else today,
        key="date_selector"
    )
    # 日期有效性验证
    formatted_date_str = selected_date.strftime('%Y%m%d')
    if trade_dates and selected_date not in trade_dates:
        past_dates = [d for d in trade_dates if d <= selected_date]
        if past_dates:
            nearest_date = max(past_dates)
            st.warning(f"⚠️ 非交易日，已自动切换至最近交易日: {nearest_date.strftime('%Y%m%d')}")
            selected_date = nearest_date
            formatted_date_str = selected_date.strftime('%Y%m%d')
        else:
            st.error("无有效交易日可供选择")
            return
    # 数据加载
    with st.spinner(f"正在加载{formatted_date_str}数据..."):
        raw_data = fetch_zt_data(formatted_date_str)
        processed_data = process_data(raw_data, formatted_date_str)
    if processed_data.empty:
        st.error(f"{formatted_date_str} 无数据")
        return
    # 界面展示
    st.title(f"{formatted_date_str} 涨停分析看板")
    # 主表格展示
    st.subheader("涨停榜单")
    st.dataframe(
        processed_data,
        use_container_width=True,
        hide_index=True,
        height=300
    )
    # 创建三列布局
    col1, col2, col3 = st.columns(3)
    # 第一列：热点行业分布
    with col1:
        st.subheader("热点行业分布")
        if '一级行业' in processed_data.columns:
            # 使用explode展开多个行业并计数
            industry_series = processed_data['一级行业'].str.split(';').explode()
            industry_series = industry_series[~industry_series.isin(exclude_concepts)]
            industry_df = industry_series.value_counts().reset_index()
            industry_df.columns = ["一级行业", "出现次数"]
            industry_df = industry_df.sort_values('出现次数', ascending=False)
            st.dataframe(industry_df, use_container_width=True, height=400)
    # 第二列：热点概念分布
    with col2:
        st.subheader("热点概念分布")
        if '概念' in processed_data.columns:
            concept_series = processed_data['概念'].str.split(';').explode()
            concept_series = concept_series[~concept_series.isin(exclude_concepts)]
            concept_df = concept_series.value_counts().reset_index()
            concept_df.columns = ["概念", "出现次数"]
            concept_df = concept_df.sort_values('出现次数', ascending=False)
            st.dataframe(concept_df, use_container_width=True, height=400)
    # 第三列：核心概念分布
    with col3:
        st.subheader("核心概念分布")
        if '核心概念' in processed_data.columns:
            core_concept_series = processed_data['核心概念'].str.split(';').explode()
            core_concept_series = core_concept_series[core_concept_series != '']
            core_concept_df = core_concept_series.value_counts().reset_index()
            core_concept_df.columns = ["核心概念", "出现次数"]
            core_concept_df = core_concept_df.sort_values('出现次数', ascending=False)
            st.dataframe(core_concept_df, use_container_width=True, height=400)
if __name__ == "__main__":
    app()