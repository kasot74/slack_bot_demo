# 定義一副撲克牌
ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
suits = ['♣️', '♠️', '♥️', '♦️']
deck = [f"{suit}{rank}" for rank in ranks for suit in suits]        
# 儲存每位使用者的牌組
user_cards = {}

# 定義牌型的大小和對應的中文名稱
hand_rankings = {
    "high_card": ("高牌", 1),
    "pair": ("一對", 2),
    "two_pair": ("兩對", 3),
    "three_of_a_kind": ("三條", 4),
    "straight": ("順子", 5),
    "flush": ("同花", 6),
    "full_house": ("葫蘆", 7),
    "four_of_a_kind": ("四條", 8),
    "straight_flush": ("同花順", 9),
    "royal_flush": ("皇家同花順", 10)
}


@app.message(re.compile(r"^!抽牌\s+(.+)$"))
def draw_cards(message, say):
    user_id = message['user']  # 獲取使用者的 ID
    channel = message['channel']

    # 嘗試抓取輸入的內容，若無輸入則預設為 1        
    num_cards_input = re.match(r"^!抽牌\s+(.+)$", message['text']).group(1).strip()                       
    
    try:
        # 嘗試將輸入轉換為整數，非整數輸入將自動設為 1
        num_cards = int(num_cards_input)
    except ValueError:
        num_cards = 1  # 非數字情況，設為 1

    # 初始化使用者的牌組
    if user_id not in user_cards:
        user_cards[user_id] = []
    
    # 計算所有使用者已抽的牌
    all_used_cards = [card for cards in user_cards.values() for card in cards]
    available_cards = list(set(deck) - set(all_used_cards))
    
    if num_cards > len(available_cards):
        say(f"剩餘牌數不足，你只能抽 {len(available_cards)} 張！", channel=channel)
        return

    # 隨機選擇多張牌
    drawn_cards = random.sample(available_cards, num_cards)
    user_cards[user_id].extend(drawn_cards)  # 記錄使用者的牌

    # 回應結果
    say(f"<@{user_id}> 抽到的是：{', '.join(drawn_cards)}", channel=channel)

@app.message(re.compile(r"^!我的牌"))
def show_user_cards(message, say):
    user_id = message['user']  # 獲取使用者的 ID
    channel = message['channel']

    if user_id in user_cards and user_cards[user_id]:
        cards = ", ".join(user_cards[user_id])
        say(f"<@{user_id}> 你擁有的牌是：{cards}", channel=channel)
    else:
        say(f"<@{user_id}> 你還沒有抽過任何牌！", channel=channel)

@app.message(re.compile(r"^!最大牌型$"))
def show_best_hand(message, say):
    user_id = message['user']  # 獲取使用者的 ID
    channel = message['channel']

    if user_id in user_cards and user_cards[user_id]:
        # 判斷使用者目前的最佳牌型
        cards = user_cards[user_id]
        hand_type, best_cards = evaluate_hand(cards)
        best_cards_display = ", ".join(best_cards)
        say(f"<@{user_id}> 最大牌型是：{hand_type}, {best_cards_display}！", channel=channel)
    else:
        say(f"<@{user_id}> 你還沒有抽過任何牌，無法判斷最大牌型！", channel=channel)      

def evaluate_hand(cards):
    # 提取數字和花色
    ranks_only = [card[2:] if card[1].isdigit() else card[1:] for card in cards]
    suits_only = [card[:2] if card[1].isdigit() else card[:1] for card in cards]

    # 判斷是否為同花
    is_flush = len(set(suits_only)) == 1
    
    # 判斷是否為順子
    sorted_ranks = sorted(ranks_only, key=lambda x: ranks.index(x))
    is_straight = all(
        ranks.index(sorted_ranks[i]) + 1 == ranks.index(sorted_ranks[i + 1])
        for i in range(len(sorted_ranks) - 1)
    )

    # 計算數字出現次數
    rank_counts = {rank: ranks_only.count(rank) for rank in ranks_only}

    # 判斷牌型
    if is_flush and is_straight:
        if sorted_ranks[-1] == 'A' and sorted_ranks[0] == '10':
            return hand_rankings["royal_flush"], cards
        return hand_rankings["straight_flush"], cards
    elif 4 in rank_counts.values():
        quad_rank = [rank for rank, count in rank_counts.items() if count == 4][0]
        best_cards = [card for card in cards if card[2:] == quad_rank or card[1:] == quad_rank]
        return hand_rankings["four_of_a_kind"], best_cards
    elif 3 in rank_counts.values() and 2 in rank_counts.values():
        triple_rank = [rank for rank, count in rank_counts.items() if count == 3][0]
        pair_rank = [rank for rank, count in rank_counts.items() if count == 2][0]
        best_cards = [card for card in cards if card[2:] in [triple_rank, pair_rank] or card[1:] in [triple_rank, pair_rank]]
        return hand_rankings["full_house"], best_cards
    elif is_flush:
        return hand_rankings["flush"], cards
    elif is_straight:
        return hand_rankings["straight"], cards
    elif 3 in rank_counts.values():
        triple_rank = [rank for rank, count in rank_counts.items() if count == 3][0]
        best_cards = [card for card in cards if card[2:] == triple_rank or card[1:] == triple_rank]
        return hand_rankings["three_of_a_kind"], best_cards
    elif list(rank_counts.values()).count(2) == 2:
        pair_ranks = [rank for rank, count in rank_counts.items() if count == 2]
        best_cards = [card for card in cards if card[2:] in pair_ranks or card[1:] in pair_ranks]
        return hand_rankings["two_pair"], best_cards
    elif 2 in rank_counts.values():
        pair_rank = [rank for rank, count in rank_counts.items() if count == 2][0]
        best_cards = [card for card in cards if card[2:] == pair_rank or card[1:] == pair_rank]
        return hand_rankings["pair"], best_cards
    else:
        highest_card = max(cards, key=lambda card: ranks.index(card[2:] if card[1].isdigit() else card[1:]))
        return hand_rankings["high_card"], [highest_card]
