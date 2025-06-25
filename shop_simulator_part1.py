import streamlit as st
import pandas as pd
import random

# -----------------------
# 基础配置
# -----------------------

CARD_QUANTITIES = {1: 30, 2: 25, 3: 18, 4: 10, 5: 9}
EXCLUDED_UNITS = {"T-43X", "R-080T"}

st.set_page_config(page_title="云顶商店模拟器", layout="centered")
st.title("🧪 云顶之弈商店模拟器 - Part 1")

# -----------------------
# 加载棋子数据
# -----------------------

@st.cache_data
def load_data():
    df = pd.read_csv("tft14_champions_cleaned.csv")
    df = df[~df["name"].isin(EXCLUDED_UNITS)]
    return df

df = load_data()

# -----------------------
# 构建卡池
# -----------------------

def initialize_pool(df):
    pool = {cost: {} for cost in CARD_QUANTITIES}
    for _, row in df.iterrows():
        name = row["name"]
        cost = row["cost"]
        pool[cost][name] = CARD_QUANTITIES[cost]
    return pool

# -----------------------
# 刷新逻辑
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
# Streamlit 界面
# -----------------------

level = st.slider("当前等级", 1, 11, 8)
if "pool" not in st.session_state:
    st.session_state["pool"] = initialize_pool(df)

if st.button("🎲 刷新商店"):
    shop = roll_shop(st.session_state["pool"], level)
    st.session_state["shop"] = shop

if "shop" in st.session_state:
    st.subheader("📍 当前商店")
    for name, cost in st.session_state["shop"]:
        st.markdown(f"- **{name}**（{cost}费）")
