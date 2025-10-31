import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime, date

# 设置页面配置
st.set_page_config(
    layout="wide",
    page_title="新发基金统计查询",
    page_icon="📊"
)

# 初始化session_state
if 'fund_data' not in st.session_state:
    st.session_state.fund_data = None
if 'last_valid_start' not in st.session_state:
    st.session_state.last_valid_start = None
if 'last_valid_end' not in st.session_state:
    st.session_state.last_valid_end = None
# <--- 新增：为基金类型多选框初始化 session_state
if 'fund_type_selection' not in st.session_state:
    st.session_state.fund_type_selection = None # 稍后在加载数据后填充

# 页面标题
st.title("新发基金统计查询工具")
st.markdown("筛选条件：选择基金类型和完整日期范围（开始+结束）后自动更新结果")

# 缓存数据获取函数
@st.cache_data(ttl=3600)
def get_fund_data():
    try:
        df = ak.fund_new_found_em()
        # 数据预处理
        if '成立日期' in df.columns:
            df['成立日期'] = pd.to_datetime(df['成立日期'])
        if '募集份额' in df.columns:
            df['募集份额'] = df['募集份额'].replace(r'[^\d.]', '', regex=True)
            df['募集份额'] = pd.to_numeric(df['募集份额'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"数据获取失败: {str(e)}")
        return None

# 首次加载数据
if st.session_state.fund_data is None:
    with st.spinner("正在获取基金数据，请稍候..."):
        st.session_state.fund_data = get_fund_data()
        
        if st.session_state.fund_data is not None and not st.session_state.fund_data.empty:
            # 初始化日期
            default_start = date(2025, 1, 1)
            today = date.today()
            data_min = st.session_state.fund_data['成立日期'].min().date()
            data_max = st.session_state.fund_data['成立日期'].max().date()
            init_start = max(default_start, data_min)
            init_end = min(today, data_max)
            st.session_state.last_valid_start = init_start
            st.session_state.last_valid_end = init_end
            
            # <--- 新增：首次加载时，默认全选所有基金类型
            if st.session_state.fund_type_selection is None:
                all_types = st.session_state.fund_data['基金类型'].unique().tolist()
                st.session_state.fund_type_selection = all_types

# 侧边栏筛选条件
st.sidebar.header("筛选条件")

# 数据有效时处理筛选
if st.session_state.fund_data is not None and not st.session_state.fund_data.empty:
    
    # 1. 基金类型筛选（多选） <--- 修改点开始
    fund_types = st.session_state.fund_data['基金类型'].unique()
    
    # 使用 st.expander 将多选框折叠起来
    with st.sidebar.expander("基金类型 (点击展开多选)", expanded=False):
        # 增加“全选”和“清空”按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("全选", use_container_width=True):
                st.session_state.fund_type_selection = fund_types.tolist()
                st.rerun() # 重新运行以更新多选框
        with col2:
            if st.button("清空", use_container_width=True):
                st.session_state.fund_type_selection = []
                st.rerun() # 重新运行以更新多选框
        
        # 将多选框放入折叠器中，并将其值与 session_state 绑定
        selected_types = st.multiselect(
            "选择基金类型",
            options=fund_types,
            # 'default' 读取 session_state 中的值
            default=st.session_state.fund_type_selection, 
            key="fund_type_multiselect" # 给多选框一个独立的key
        )
        
        # <--- 新增：同步多选框的最新选择到 session_state
        # 这确保了即使用户手动选择，状态也能被正确保存
        if selected_types != st.session_state.fund_type_selection:
            st.session_state.fund_type_selection = selected_types
            st.rerun()

    # <--- 修改：确保 selected_types 变量在筛选时是正确的
    # (如果用户没有展开折叠器，我们仍然使用 session_state 中的值)
    selected_types = st.session_state.fund_type_selection
    # <--- 修改点结束
    
    
    # 2. 日期范围筛选
    data_min_date = st.session_state.fund_data['成立日期'].min().date()
    data_max_date = st.session_state.fund_data['成立日期'].max().date()
    
    date_input = st.sidebar.date_input(
        "成立日期范围",
        value=[
            st.session_state.last_valid_start,
            st.session_state.last_valid_end
        ],
        min_value=data_min_date,
        max_value=data_max_date,
        key="date_range",
        help="请先选择开始日期，再选择结束日期（需完整选择两个日期）"
    )
    
    # 3. 检查日期输入，并确定当前要使用的日期
    valid_date = False
    current_start = None
    current_end = None
    
    if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
        temp_start, temp_end = date_input
        if temp_start <= temp_end:
            valid_date = True
            current_start = temp_start
            current_end = temp_end
            st.session_state.last_valid_start = current_start
            st.session_state.last_valid_end = current_end
        else:
            st.sidebar.error("⚠️ 开始日期不能晚于结束日期")
    else:
        st.sidebar.info("⏳ 请完整选择开始日期和结束日期（先点开始，再点结束）")
    
    if not valid_date:
        current_start = st.session_state.last_valid_start
        current_end = st.session_state.last_valid_end
    
    # 4. 执行筛选（始终执行）
    start_dt = pd.to_datetime(current_start)
    end_dt = pd.to_datetime(current_end)
    
    # <--- 修改：确保 selected_types 不为 None
    if selected_types is None:
        selected_types = []
    
    filtered_df = st.session_state.fund_data[
        (st.session_state.fund_data['基金类型'].isin(selected_types)) &
        (st.session_state.fund_data['成立日期'] >= start_dt) &
        (st.session_state.fund_data['成立日期'] <= end_dt)
    ]
    
    # 5. 显示结果
    if filtered_df is not None and not filtered_df.empty:
        st.subheader(f"筛选结果（共 {len(filtered_df)} 条）")
        
        if '募集份额' in filtered_df.columns:
            valid_share = filtered_df.dropna(subset=['募集份额'])['募集份额']
            if not valid_share.empty:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总募集份额（亿份）", f"{valid_share.sum():.2f}")
                with col2:
                    st.metric("平均募集份额（亿份）", f"{valid_share.mean():.2f}")
                with col3:
                    st.metric("最大募集份额（亿份）", f"{valid_share.max():.2f}")
                with col4:
                    st.metric("最小募集份额（亿份）", f"{valid_share.min():.2f}")
                st.divider()
        
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("未找到符合条件的数据，请调整筛选条件")

else:
    if st.session_state.fund_data is None:
        st.warning("正在获取数据，请稍候...")
    else:
        st.warning("未获取到有效基金数据")

# 数据来源说明
st.caption("数据来源：akshare - 东方财富网新成立基金数据")