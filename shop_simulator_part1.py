
import streamlit as st
import pandas as pd
import random
from collections import Counter

# -----------------------
# 基础配置
# -----------------------

CARD_QUANTITIES = {1: 30, 2: 25, 3: 18, 4: 10, 5: 9}
EXCLUDED_UNITS = {"T-43X", "R-080T"}

st.set_page_config(page_title="云顶商店模拟器 - Part 3", layout="centered")
st.title("🌟 云顶之弈商店模拟器 - Part 3")

# -----------------------
# 加载数据
# -----------------------

@st.cache_data
def load_data():
    df = pd.read_csv("tft14_champions_cleaned.csv")
    df = df[~df["name"].isin(EXCLUDED_UNITS)]
    return df

df = load_data()

# -----------------------
# 初始化状态
# -----------------------

if "pool" not in st.session_state:
    pool = {cost: {} for cost in CARD_QUANTITIES}
    for _, row in df.iterrows():
        name = row["name"]
        cost = row["cost"]
        pool[cost][name] = CARD_QUANTITIES[cost]
    st.session_state["pool"] = pool

if "gold" not in st.session_state:
    st.session_state["gold"] = 10

if "shop" not in st.session_state:
    st.session_state["shop"] = []

if "bench" not in st.session_state:
    st.session_state["bench"] = []

if "lock_shop" not in st.session_state:
    st.session_state["lock_shop"] = False

# -----------------------
# 升星逻辑
# -----------------------

def auto_upgrade(bench):
    counts = Counter(bench)
    for name, qty in counts.items():
        while qty >= 3:
            bench.remove(name)
            bench.remove(name)
            bench.remove(name)
            bench.append(name + "⭐")
            qty -= 3
    return bench

# -----------------------
# 概率与刷新逻辑
# -----------------------

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
    }.get(level, {1: 1.0})

def roll_shop(pool, level):
    shop = []
    odds = get_shop_odds(level)
    for _ in range(5):
        costs = list(odds.keys())
        probs = list(odds.values())
        chosen_cost = random.choices(costs, weights=probs, k=1)[0]
        available = pool.get(chosen_cost, {})
        remaining = {n: c for n, c in available.items() if c > 0}
        if remaining:
            cards = list(remaining.keys())
            weights = list(remaining.values())
            chosen_card = random.choices(cards, weights=weights, k=1)[0]
            shop.append((chosen_card, chosen_cost))
    return shop

# -----------------------
# 控件 UI
# -----------------------


level = st.slider("当前等级", 1, 11, 8)

# 显示当前等级下的刷新概率
st.markdown("🎯 **当前刷新概率：**")
current_odds = get_shop_odds(level)
odds_text = "｜".join([f"{cost}费：{int(p*100)}%" for cost, p in current_odds.items()])
st.info(odds_text)

gold_input = st.number_input("🧮 当前金币（可修改）", min_value=0, max_value=100, value=max(0, st.session_state["gold"]))
st.session_state["gold"] = gold_input

cols = st.columns([1, 1])
with cols[0]:
    if st.button("🔁 刷新商店（-2金币）", disabled=st.session_state["gold"] < 2):
        if not st.session_state["lock_shop"]:
            st.session_state["shop"] = roll_shop(st.session_state["pool"], level)
        st.session_state["gold"] = max(0, st.session_state["gold"] - 2)
with cols[1]:
    st.toggle("🔒 锁定商店", key="lock_shop")

# -----------------------
# 商店展示与购买
# -----------------------

st.subheader("🛒 当前商店")
for idx, (name, cost) in enumerate(st.session_state["shop"]):
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown(f"- **{name}**（{cost}费）")
    with cols[1]:
        if st.button(f"购买", key=f"buy_{idx}", disabled=st.session_state["gold"] < cost or name == "—"):
            st.session_state["gold"] = max(0, st.session_state["gold"] - cost)
            st.session_state["bench"].append(name)
            st.session_state["pool"][cost][name] -= 1
            st.session_state["shop"][idx] = ("—", 0)
            st.session_state["bench"] = auto_upgrade(st.session_state["bench"])

# -----------------------
# 手牌展示
# -----------------------



st.subheader("🎒 手牌区（Bench）")
if st.session_state["bench"]:
    for idx, unit in enumerate(st.session_state["bench"]):
        cols = st.columns([4, 1])
        with cols[0]:
            st.markdown(f"**{unit}**")
        with cols[1]:
            if st.button("出售", key=f"sell_{idx}"):
                st.session_state["bench"].pop(idx)
                base_name = unit.replace("⭐", "")
                cost = int(df[df["name"] == base_name]["cost"].values[0])
                st.session_state["gold"] = min(100, st.session_state["gold"] + cost)
                if base_name in st.session_state["pool"][cost]:
                    st.session_state["pool"][cost][base_name] += 1
                st.rerun()
else:
    st.write("（暂无）")


