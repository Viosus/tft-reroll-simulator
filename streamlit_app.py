
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


# --- 用户设置目标卡区域 ---
st.subheader("🎯 设置你的目标卡")
add_row = st.button("➕ 添加一张目标卡")
if add_row:
    st.session_state["target_rows"].append({"name": champion_names[0], "count": 3, "remain": 30})
    st.rerun()

targets = {}
custom_pool_counts = {}

for idx, row in enumerate(st.session_state["target_rows"]):
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        name = st.selectbox("卡牌", champion_names, index=champion_names.index(row["name"]), key=f"target_name_{idx}")
    with col2:
        count = st.number_input("需求张数", min_value=1, max_value=9, value=row["count"], key=f"target_count_{idx}")
    with col3:
        remain = st.number_input("卡池剩余", min_value=0, max_value=30, value=row["remain"], key=f"target_remain_{idx}")
    with col4:
        if st.button("🗑️ 删除", key=f"target_delete_{idx}"):
            st.session_state["target_rows"].pop(idx)
            st.rerun()
    targets[name] = count
    custom_pool_counts[name] = remain
    # 更新状态
    st.session_state["target_rows"][idx] = {"name": name, "count": count, "remain": remain}

# --- 模拟部分 ---
level = st.slider("选择刷新等级", min_value=1, max_value=11, value=8)
runs = st.number_input("模拟次数", min_value=1, max_value=5000, value=500)

def get_shop_odds(level):
    SHOP_ODDS = {
        1: {1: 1.00}, 2: {1: 1.00}, 3: {1: 0.75, 2: 0.25},
        4: {1: 0.55, 2: 0.30, 3: 0.15}, 5: {1: 0.45, 2: 0.33, 3: 0.20, 4: 0.02},
        6: {1: 0.30, 2: 0.40, 3: 0.25, 4: 0.05}, 7: {1: 0.19, 2: 0.30, 3: 0.40, 4: 0.10, 5: 0.01},
        8: {1: 0.17, 2: 0.24, 3: 0.32, 4: 0.24, 5: 0.03}, 9: {1: 0.15, 2: 0.18, 3: 0.25, 4: 0.30, 5: 0.12},
        10: {1: 0.05, 2: 0.10, 3: 0.20, 4: 0.40, 5: 0.25}, 11: {1: 0.01, 2: 0.02, 3: 0.12, 4: 0.50, 5: 0.35}
    }
    return SHOP_ODDS.get(level, {})

def roll_shop(pool, level, target_dict):
    odds = get_shop_odds(level)
    hits = {name: 0 for name in target_dict}
    for _ in range(5):
        cost = random.choices(list(odds.keys()), weights=list(odds.values()), k=1)[0]
        cards = pool.get(cost, {})
        remaining = {n: c for n, c in cards.items() if c > 0}
        if not remaining:
            continue
        weights = list(remaining.values())
        chosen_card = random.choices(list(remaining.keys()), weights=weights, k=1)[0]
        if chosen_card in hits:
            pool[cost][chosen_card] -= 1
            hits[chosen_card] += 1
    return hits

def simulate_to_targets(level, df, targets, custom_pool_counts, cost_removal, specific_removal):
    pool = build_card_pool(df, targets, cost_removal, specific_removal)
    current = {name: 0 for name in targets}
    rolls = 0
    while any(current[name] < targets[name] for name in targets):
        result = roll_shop(pool, level, targets)
        for name, hit in result.items():
            current[name] += hit
        rolls += 1
    cost = rolls * 2 + sum(targets.values()) * 4
    return cost

if st.button("🎲 开始模拟"):
    results = [simulate_to_targets(level, df, targets, custom_pool_counts,
                                   st.session_state["cost_removal"],
                                   st.session_state["specific_removal"]) for _ in range(runs)]
    avg = sum(results) / len(results)
    st.session_state["history"].append((targets.copy(), avg))
    st.success(f"平均总花费：{avg:.2f} 金币（含抽卡 + 购买）")

    fig, ax = plt.subplots()
    ax.hist(results, bins=20, edgecolor='black')
    ax.set_title("🎯 模拟金币分布")
    ax.set_xlabel("金币总花费")
    ax.set_ylabel("次数")
    st.pyplot(fig)

# --- 历史记录 ---
if st.session_state["history"]:
    st.subheader("📜 历史记录")
    for i, (setting, avg) in enumerate(reversed(st.session_state["history"][-5:])):
        cards = ", ".join([f"{k}x{v}" for k, v in setting.items()])
        st.markdown(f"{len(st.session_state['history']) - i}. `{cards}` → **{avg:.2f} 金币**")
