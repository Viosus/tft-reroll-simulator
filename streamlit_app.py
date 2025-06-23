
import streamlit as st
import pandas as pd
import random
import matplotlib.pyplot as plt

CARD_QUANTITIES = {1: 30, 2: 25, 3: 18, 4: 10, 5: 9}
EXCLUDED_UNITS = {"T-43X", "R-080T"}

# 初始化状态
if "target_rows" not in st.session_state:
    st.session_state["target_rows"] = []
if "history" not in st.session_state:
    st.session_state["history"] = []
if "cost_removal" not in st.session_state:
    st.session_state["cost_removal"] = {i: 0 for i in range(1, 6)}
if "specific_removal" not in st.session_state:
    st.session_state["specific_removal"] = []

df = pd.read_csv("tft14_champions_cleaned.csv")
champion_names = sorted(df[~df["name"].isin(EXCLUDED_UNITS)]["name"].unique())

st.title("云顶之弈 D 卡模拟器 v1.9")
st.caption("支持费用池卡牌减少设定 + 精细设定特定卡已被抽走")


# --- 费用卡牌总数扣除设定 ---
with st.expander("🔧 每费用位减少的卡牌总数"):
    for cost in range(1, 6):
        st.session_state["cost_removal"][cost] = st.number_input(
            f"{cost}费卡被其他玩家拿走的总数",
            min_value=0,
            max_value=CARD_QUANTITIES[cost] * len(df[df['cost'] == cost]),
            value=st.session_state["cost_removal"][cost],
            step=1,
            key=f"cost_remove_{cost}"
        )

# --- 精细移除卡牌设定 ---
with st.expander("🔍 指定具体卡牌被拿走的数量（不参与模拟）"):
    add_specific = st.checkbox("添加一行卡牌移除设定")
    if add_specific:
        col1, col2 = st.columns([2, 1])
        with col1:
            chosen = st.selectbox("选择卡牌", champion_names, key="specific_add_name")
        with col2:
            amt = st.number_input("移除张数", min_value=1, max_value=30, value=1, step=1, key="specific_add_amt")
        if st.button("➕ 添加这张卡"):
            st.session_state["specific_removal"].append({"name": chosen, "count": amt})
            st.rerun()

    for idx, item in enumerate(st.session_state["specific_removal"]):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.text_input("卡牌名", value=item["name"], disabled=True, key=f"specific_show_{idx}")
        with col2:
            st.number_input("数量", value=item["count"], min_value=1, max_value=30, key=f"specific_amt_{idx}", disabled=True)
        with col3:
            if st.button("🗑️ 删除", key=f"remove_specific_{idx}"):
                st.session_state["specific_removal"].pop(idx)
                st.rerun()

# --- 构建卡池函数（综合目标卡、自定义移除、精细移除） ---
def build_card_pool(df, targets, cost_removal, specific_removal):
    pool = {cost: {} for cost in CARD_QUANTITIES}
    targets_set = set(targets.keys())

    # 1. 构建原始卡池
    for _, row in df.iterrows():
        name = row["name"]
        cost = row["cost"]
        if name in EXCLUDED_UNITS:
            continue
        pool[cost][name] = CARD_QUANTITIES[cost]

    # 2. 应用目标卡设定（强制设定）
    for name, need in targets.items():
        cost = int(df[df["name"] == name]["cost"].values[0])
        pool[cost][name] = custom_pool_counts.get(name, CARD_QUANTITIES[cost])

    # 3. 精细移除指定卡（跳过目标卡）
    for item in specific_removal:
        name = item["name"]
        count = item["count"]
        if name in targets_set:
            continue
        cost = int(df[df["name"] == name]["cost"].values[0])
        if name in pool[cost]:
            pool[cost][name] = max(0, pool[cost][name] - count)

    # 4. 同费用扣除（排除目标卡 + 精细指定卡）
    for cost in range(1, 6):
        total_removal = cost_removal[cost]
        non_target_cards = [n for n in pool[cost] if n not in targets_set and
                            n not in [s["name"] for s in specific_removal]]
        if not non_target_cards or total_removal <= 0:
            continue
        per_card_removal = total_removal // len(non_target_cards)
        remainder = total_removal % len(non_target_cards)
        for i, name in enumerate(non_target_cards):
            deduct = per_card_removal + (1 if i < remainder else 0)
            pool[cost][name] = max(0, pool[cost][name] - deduct)

    return pool
