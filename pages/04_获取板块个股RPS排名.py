import streamlit as st
import pywencai
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
# 设置页面配置
st.set_page_config(page_title="股票RPS强度排名", layout="wide")
st.title("股票RPS强度排名分析")
# 日期计算函数
def get_date_range(days):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")
# RPS计算函数
def calculate_rps(df, change_col):
    df[change_col] = pd.to_numeric(df[change_col].astype(str).str.replace('%', ''), errors='coerce')
    df['rank'] = df[change_col].rank(ascending=False, method='min')
    total_count = len(df)
    df['RPS'] = ((1 - df['rank'] / total_count) * 100).round(2)
    df.drop('rank', axis=1, inplace=True)
    return df
# 获取数据函数
def get_index_data(period, concept):
    start_date, end_date = get_date_range(period)
    query = f"近{period}日涨跌幅，{concept}"
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
        df = pywencai.get(query=query, loop=True, headers=headers)
        if df is None:
            st.warning(f"pywencai 未返回任何数据（可能接口调用失败）")
            return None
        if df.empty:
            st.warning(f"未获取到近{period}日数据")
            return None
        # 查找相关列
        change_col = next((col for col in df.columns if "区间涨跌幅" in col), None)
        code_col = next((col for col in df.columns if "股票代码" in col), None)
        name_col = next((col for col in df.columns if "股票简称" in col), None)
        if not all([change_col, code_col, name_col]):
            st.warning(f"未找到必要的列")
            return None
        # 提取关键列
        result_df = df[[code_col, name_col, change_col]].copy()
        result_df.columns = ['股票代码', '股票简称', f'{period}日涨跌幅']
        # 计算RPS
        result_df = calculate_rps(result_df, f'{period}日涨跌幅')
        result_df.rename(columns={'RPS': f'RPS_{period}'}, inplace=True)
        return result_df
    except Exception as e:
        st.error(f"获取近{period}日数据失败: {str(e)}")
        return None
# 主程序
def app():
    # 概念输入框
    concept = st.text_input("输入股票概念", value="机器人概念",
                            placeholder="请输入股票概念，如'人工智能'、'新能源汽车'等")
    # 时间范围选择
    periods = st.multiselect(
        "选择时间范围",
        [5, 20, 60],
        default=[5, 20, 60]
    )
    # RPS筛选阈值
    rps_threshold = st.number_input(
        "RPS筛选阈值 (0-100)",
        min_value=0,
        max_value=100,
        value=90,
        help="只显示所有选定周期RPS都大于该值的股票，设置为0则显示全部"
    )
    # 数据获取按钮
    if st.button("获取数据"):
        if not concept:
            st.error("请输入股票概念")
            return
        if not periods:
            st.error("请选择至少一个时间范围")
            return
        with st.spinner("正在获取数据..."):
            dataframes = {}
            for period in periods:
                df = get_index_data(period, concept)
                if df is not None:
                    dataframes[period] = df
            if not dataframes:
                st.error("未获取到任何数据，原因not dataframes")
                return
            # 合并数据
            merged_df = None
            for i, period in enumerate(periods):
                if i == 0:
                    merged_df = dataframes[period]
                else:
                    merged_df = pd.merge(
                        merged_df,
                        dataframes[period],
                        on=['股票代码', '股票简称'],
                        how='outer'
                    )
            # 应用RPS筛选 - 修改为所有周期都必须满足条件
            if rps_threshold > 0:
                # 创建筛选条件：所有选定周期的RPS都必须大于阈值
                filter_condition = True
                for period in periods:
                    rps_col = f'RPS_{period}'
                    if rps_col in merged_df.columns:
                        filter_condition = filter_condition & (merged_df[rps_col] > rps_threshold)
                    else:
                        st.warning(f"未找到{period}日RPS数据")
                        filter_condition = False
                        break
                if filter_condition is not False:
                    filtered_df = merged_df[filter_condition].copy()
                else:
                    filtered_df = merged_df
            else:
                filtered_df = merged_df
            # 显示结果
            st.subheader(f"'{concept}'概念股票RPS强度排名 ({', '.join(map(str, periods))}日)")
            if len(filtered_df) == 0:
                st.warning(f"没有找到所有周期RPS都大于{rps_threshold}的股票")
                # 显示全部数据
                st.info("显示全部股票数据:")
                display_df = merged_df.sort_values(by=[f'RPS_{p}' for p in periods], ascending=False)
            else:
                display_df = filtered_df.sort_values(by=[f'RPS_{p}' for p in periods], ascending=False)
                st.info(f"找到 {len(filtered_df)} 只所有周期RPS都大于{rps_threshold}的股票")
            st.dataframe(
                display_df,
                use_container_width=True,
                height=600
            )
            # 下载按钮 - 下载全部数据而非筛选后的数据
            csv = merged_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="下载CSV数据(全部)",
                data=csv,
                file_name=f"{concept}_股票RPS排名_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv'
            )
# 运行主程序
if __name__ == "__main__":
    app() 

