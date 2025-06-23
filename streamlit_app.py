
import streamlit as st
import pandas as pd
import random
import matplotlib.pyplot as plt

# 卡池设定
CARD_QUANTITIES = {1: 30, 2: 25, 3: 18, 4: 10, 5: 9}
EXCLUDED_UNITS = {"T-43X", "R-080T"}

# 初始化状态
if "target_rows" not in st.session_state:
    st.session_state["target_rows"] = []
if "history" not in st.session_state:
    st.session_state["history"] = []

# 数据加载
df = pd.read_csv("tft14_champions_cleaned.csv")
champion_names = sorted(df[~df["name"].isin(EXCLUDED_UNITS)]["name"].unique())

# 页面主标题
st.title("云顶之弈 D 卡模拟器")
st.caption("版本号：v1.8 - 移除卡数控件，完全动态添加/删除")

# 等级选择
level = st.slider("选择刷新等级", min_value=1, max_value=11, value=8)

# 添加新卡设定
with st.expander("➕ 添加目标卡"):
    col1, col2 = st.columns([2, 1])
    with col1:
        new_name = st.selectbox("选择卡牌", champion_names, key="add_name")
    with col2:
        default_cost = int(df[df["name"] == new_name]["cost"].values[0])
        default_max = CARD_QUANTITIES.get(default_cost, 30)
        new_count = st.number_input("需求张数", min_value=1, max_value=9, value=3, key="add_count")
        new_remaining = st.number_input("卡池剩余", min_value=0, max_value=30, value=default_max, key="add_remain")
    if st.button("添加卡牌"):
        st.session_state["target_rows"].append({
            "name": new_name,
            "count": new_count,
            "remaining": new_remaining
        })
        st.rerun()

# 当前目标卡表单
targets = {}
custom_pool_counts = {}

for idx, row in enumerate(st.session_state["target_rows"]):
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        name = st.selectbox(f"卡牌 {idx+1}", champion_names, index=champion_names.index(row["name"]), key=f"name_{idx}")
    with col2:
        count = st.number_input(f"需求张数", min_value=1, max_value=9, value=row["count"], key=f"count_{idx}")
    with col3:
        default_cost = int(df[df["name"] == name]["cost"].values[0])
        default_max = CARD_QUANTITIES.get(default_cost, 30)
        remaining = st.number_input("卡池剩余", min_value=0, max_value=30, value=row["remaining"], key=f"remain_{idx}")
    with col4:
        if st.button("🗑️ 删除", key=f"delete_{idx}"):
            st.session_state["target_rows"].pop(idx)
            st.rerun()
    targets[name] = count
    custom_pool_counts[name] = remaining


# 💠 每费用卡池卡牌总数调整（不影响目标卡）
with st.expander("⚙️ 费用位卡池总数调整（假设其他玩家已拿走）"):
    cost_taken_adjust = {}
    for cost in range(1, 6):
        cost_taken_adjust[cost] = st.number_input(f"{cost}费减少张数", min_value=0, max_value=CARD_QUANTITIES[cost] * 13, value=0, step=1, key=f"cost_adj_{cost}")
else_removed_card_info = cost_taken_adjust





# 💠 精细设定被其他玩家拿走的特定卡牌（不会作为目标卡）
if "custom_taken_cards" not in st.session_state:
    st.session_state["custom_taken_cards"] = {}

with st.expander("🧩 指定被拿走的非目标卡"):
    custom_taken_cards = {}
    for cost in range(1, 6):
        st.markdown(f"**{cost}费卡牌**")
        sub_df = df[(df["cost"] == cost) & (~df["name"].isin(EXCLUDED_UNITS))]
        non_target_cards = [n for n in sub_df["name"] if n not in custom_pool_counts]
        total_to_remove = cost_taken_adjust.get(cost, 0)

        # === 正确分配：总数 = total_to_remove ===
        base = total_to_remove // max(1, len(non_target_cards))
        extra = total_to_remove % max(1, len(non_target_cards))
        distribution = {}
        for i, name in enumerate(non_target_cards):
            distribution[name] = base + (1 if i < extra else 0)
            distribution[name] = min(distribution[name], CARD_QUANTITIES[cost])  # 不超过最大值

        for name in non_target_cards:
            key = f"custom_taken_{name}"
            if key not in st.session_state["custom_taken_cards"]:
                st.session_state["custom_taken_cards"][key] = distribution[name]

        for name in non_target_cards:
            key = f"custom_taken_{name}"
            new_val = st.number_input(
                f"{name} 被拿走数量",
                min_value=0,
                max_value=CARD_QUANTITIES[cost],
                value=st.session_state["custom_taken_cards"].get(key, 0),
                step=1,
                key=key
            )
            custom_taken_cards[name] = new_val
            st.session_state["custom_taken_cards"][key] = new_val

else_taken_named_card_info = custom_taken_cards








# 当前卡池状态展示
current_pool = {cost: 0 for cost in CARD_QUANTITIES}
total_cards = 0
pool = {cost: {} for cost in CARD_QUANTITIES}

# 构建卡池，考虑费用位减少设定（功能1）和目标卡保护
# 构建卡池，考虑功能1和功能2：费用位减少 + 精细移除非目标卡
for _, row in df.iterrows():
    name = row["name"]
    cost = row["cost"]
    if name in EXCLUDED_UNITS:
        continue
    is_target = name in custom_pool_counts
    if is_target:
        qty = custom_pool_counts[name]
    else:
        qty = CARD_QUANTITIES[cost]
    if name in else_taken_named_card_info:
        qty -= else_taken_named_card_info[name]
        qty = max(0, qty)
    pool[cost][name] = qty

# 补足每费用被拿走的数量（扣除已被精细指定的）
for cost in range(1, 6):
    removed = cost_taken_adjust.get(cost, 0)
    non_target_units = [n for n in pool[cost] if n not in custom_pool_counts and n not in else_taken_named_card_info]
    while removed > 0 and non_target_units:
        for unit in non_target_units:
            if pool[cost][unit] > 0:
                pool[cost][unit] -= 1
                removed -= 1
                if removed <= 0:
                    break
# 汇总当前卡池信息
# 汇总当前卡池信息
current_pool = {cost: sum(pool[cost].values()) for cost in pool}
total_cards = sum(current_pool.values())

with st.expander("📦 当前卡池状态"):
    st.write(f"总卡数：{total_cards}")
    for cost in sorted(current_pool.keys()):
        st.write(f"{cost}费：{current_pool[cost]} 张")

for cost in sorted(pool.keys()):
    current_pool[cost] = sum(pool[cost].values())
    total_cards += current_pool[cost]


# 模拟核心逻辑
def get_shop_odds(level):
    return {
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
    }.get(level, {})

def roll_once_multi(level, pool, target_dict):
    odds = get_shop_odds(level)
    hits = {name: 0 for name in target_dict}
    for _ in range(5):
        for _ in range(10):
            costs = list(odds.keys())
            probs = list(odds.values())
            chosen_cost = random.choices(costs, weights=probs, k=1)[0]
            available = pool.get(chosen_cost, {})
            remaining = {n: c for n, c in available.items() if c > 0}
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

# 模拟控制
runs = st.number_input("模拟次数", min_value=1, max_value=10000, value=1000)
if st.button("开始模拟") and targets:
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

    # 保存历史记录
    st.session_state["history"].append({
        "等级": level,
        "目标卡": targets,
        "模拟次数": runs,
        "平均金币": round(total_gold, 2)
    })

# 展示历史记录
if st.session_state["history"]:
    with st.expander("🕓 历史模拟记录"):
        for i, entry in enumerate(st.session_state["history"][::-1], 1):
            st.markdown(f"**#{i} 等级 {entry['等级']}** ｜ 目标卡：{entry['目标卡']} ｜ {entry['模拟次数']} 次 ｜ 平均总花费：{entry['平均金币']} 金币")
