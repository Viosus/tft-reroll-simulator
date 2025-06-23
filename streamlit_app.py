
import streamlit as st
import pandas as pd
import random
import matplotlib.pyplot as plt

# 卡池设定
CARD_QUANTITIES = {1: 30, 2: 25, 3: 18, 4: 10, 5: 9}
EXCLUDED_UNITS = {"T-43X", "R-080T"}

def get_shop_odds(level):
    SHOP_ODDS = {
        1: {1: 1.00, 2: 0, 3: 0, 4: 0, 5: 0},
        2: {1: 1.00, 2: 0, 3: 0, 4: 0, 5: 0},
        3: {1: 0.75, 2: 0.25, 3: 0, 4: 0, 5: 0},
        4: {1: 0.55, 2: 0.30, 3: 0.15, 4: 0, 5: 0},
        5: {1: 0.45, 2: 0.33, 3: 0.20, 4: 0.02, 5: 0},
        6: {1: 0.30, 2: 0.40, 3: 0.25, 4: 0.05, 5: 0},
        7: {1: 0.19, 2: 0.30, 3: 0.40, 4: 0.10, 5: 0.01},
        8: {1: 0.17, 2: 0.24, 3: 0.32, 4: 0.24, 5: 0.03},
        9: {1: 0.15, 2: 0.18, 3: 0.25, 4: 0.30, 5: 0.12},
        10: {1: 0.05, 2: 0.10, 3: 0.20, 4: 0.40, 5: 0.25},
        11: {1: 0.01, 2: 0.02, 3: 0.12, 4: 0.50, 5: 0.35}
    }
    return SHOP_ODDS.get(level, {})

def roll_once_multi(level, pool, target_dict):
    odds = get_shop_odds(level)
    hits = {name: 0 for name in target_dict}
    for _ in range(5):  # 每格商店
        for _ in range(10):  # 最多尝试 10 次找非空费用卡池
            costs = list(odds.keys())
            probs = list(odds.values())
            chosen_cost = random.choices(costs, weights=probs, k=1)[0]
            available_cards = pool.get(chosen_cost, {})
            remaining = {n: c for n, c in available_cards.items() if c > 0}
            if remaining:
                cards = list(remaining.keys())
                weights = list(remaining.values())
                chosen_card = random.choices(cards, weights=weights, k=1)[0]
                if chosen_card in target_dict:
                    pool[chosen_cost][chosen_card] -= 1
                    hits[chosen_card] += 1
                break
    return hits

def simulate_to_targets(level, df, target_dict, custom_pool_counts=None):
    pool = {cost: {} for cost in CARD_QUANTITIES}
    for _, row in df.iterrows():
        name = row["name"]
        cost = row["cost"]
        if name in EXCLUDED_UNITS:
            continue
        if custom_pool_counts and name in custom_pool_counts:
            pool[cost][name] = custom_pool_counts[name]
        else:
            pool[cost][name] = CARD_QUANTITIES[cost]
    current_counts = {name: 0 for name in target_dict}
    rolls = 0
    while any(current_counts[name] < target_dict[name] for name in target_dict):
        hits = roll_once_multi(level, pool, target_dict)
        for name in hits:
            current_counts[name] += hits[name]
        rolls += 1
    return rolls * 2



# 初始化 session_state 容器
if "history" not in st.session_state:
    st.session_state["history"] = []
if "deleted_rows" not in st.session_state:
    st.session_state["deleted_rows"] = set()

if "history" not in st.session_state:
    st.session_state["history"] = []

# --- Streamlit 网页 ---

st.title("云顶之弈 D 卡模拟器")
st.caption("版本号：v1.3 - 修复权重概率与空格逻辑")

df = pd.read_csv("tft14_champions_cleaned.csv")
champion_names = sorted(df[~df["name"].isin(EXCLUDED_UNITS)]["name"].unique())

level = st.slider("选择刷新等级", min_value=1, max_value=11, value=8)

num_targets = st.number_input("需要模拟的目标卡数量", min_value=1, max_value=10, value=2)
targets = {}
deleted_rows = st.session_state["deleted_rows"]
custom_pool_counts = {}


for i in range(num_targets):
    if i in deleted_rows:
        continue

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        name = st.selectbox(f"第 {i+1} 张卡", champion_names, key=f"name_{i}")
    with col2:
        count = st.number_input(f"需求张数", min_value=1, max_value=9, value=3, key=f"count_{i}")
    with col3:
        default_cost = int(df[df["name"] == name]["cost"].values[0])
        default_max = CARD_QUANTITIES.get(default_cost, 30)
        remaining = st.number_input(f"卡池剩余", min_value=0, max_value=30, value=default_max, key=f"remain_{i}")
    targets[name] = count
    custom_pool_counts[name] = remaining
    if st.button("🗑️ 删除", key=f"delete_{i}"):
        deleted_rows.add(i)
        st.session_state["deleted_rows"] = deleted_rows
        st.rerun()


runs = st.number_input("模拟次数", min_value=1, max_value=10000, value=1000)

# ==== 实时显示当前卡池状态 ====
current_pool = {cost: 0 for cost in CARD_QUANTITIES}
total_cards = 0
for _, row in df.iterrows():
    name = row["name"]
    cost = row["cost"]
    if name in EXCLUDED_UNITS:
        continue
    qty = custom_pool_counts.get(name, CARD_QUANTITIES[cost])
    current_pool[cost] += qty
    total_cards += qty

with st.expander("📦 当前卡池状态"):
    st.write(f"总卡数：{total_cards}")
    for cost in sorted(current_pool.keys()):
        st.write(f"{cost}费：{current_pool[cost]} 张")


if st.button("开始模拟"):
    results = [simulate_to_targets(level, df, targets, custom_pool_counts) for _ in range(runs)]

    avg_d_gold = sum(results) / len(results)
    buy_gold = sum([df[df["name"] == name]["cost"].values[0] * count for name, count in targets.items()])
    total_gold = avg_d_gold + buy_gold
    st.write(f"平均刷新花费：{avg_d_gold:.2f} 金币")
    st.write(f"购买卡牌花费：{buy_gold} 金币")
    st.success(f"💰 平均总花费：{total_gold:.2f} 金币")


    fig, ax = plt.subplots()
    ax.hist(results, bins=20, edgecolor='black')
    ax.set_title("Distribution of Gold Spent")
    ax.set_xlabel("Gold")
    ax.set_ylabel("Simulation")

    st.pyplot(fig)

    # === 保存历史记录 ===
    st.session_state["history"].append({
        "等级": level,
        "目标卡": targets,
        "模拟次数": runs,
        "平均金币": round(sum(results) / len(results), 2)
    })

    # 展示历史记录
    with st.expander("🕓 历史模拟记录"):
        for i, entry in enumerate(st.session_state["history"][::-1], 1):
            st.markdown(f"**#{i} 等级 {entry['等级']}** ｜ 目标卡：{entry['目标卡']} ｜ {entry['模拟次数']} 次 ｜ 平均金币：{entry['平均金币']}")

