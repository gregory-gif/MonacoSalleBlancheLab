from dataclasses import dataclass

@dataclass
class TierConfig:
    level: int
    min_ga: float
    max_ga: float
    base_unit: float
    press_unit: float
    stop_loss: float
    profit_lock: float
    catastrophic_cap: float

# --- TIER GENERATION (Supports Baccarat €100 & Roulette €5) ---

def generate_tier_map(safety_factor: int = 25, mode: str = 'Standard', game_type: str = 'Baccarat') -> dict:
    tiers = {}
    
    # 1. DETERMINE BASE UNIT
    if game_type == 'Roulette':
        BASE_BET_T1 = 5.0 # Monaco Roulette Min
    else:
        BASE_BET_T1 = 100.0 # Monaco Baccarat Min

    # --- SAFE TITAN / TITAN LOGIC ---
    if mode == 'Safe Titan' or mode == 'Titan':
        # Roulette Titan: 5 -> 10 -> 20
        # Baccarat Titan: 100 -> 150 -> 250
        
        if game_type == 'Roulette':
            t1_base, t1_press = 5.0, 5.0   # 5 -> 10
            t2_base, t2_press = 10.0, 10.0 # 10 -> 20
            t3_base, t3_press = 20.0, 20.0 # 20 -> 40
            # Thresholds scaled by ~20x less
            th_low = 1000.0
            th_high = 2500.0
        else:
            t1_base, t1_press = 100.0, 100.0
            t2_base, t2_press = 100.0, 150.0
            t3_base, t3_press = 150.0, 250.0
            th_low = 2000.0
            th_high = 5000.0

        # Tier 1 (Defense)
        tiers[1] = TierConfig(
            level=1, min_ga=0, max_ga=(float('inf') if mode == 'Safe Titan' else th_low),
            base_unit=t1_base, press_unit=t1_press,
            stop_loss=-(t1_base*10), profit_lock=t1_base*6, catastrophic_cap=-(t1_base*20)
        )
        
        if mode == 'Safe Titan': return tiers # Stop here for Safe Titan

        # Tier 2 (Standard)
        tiers[2] = TierConfig(
            level=2, min_ga=th_low, max_ga=float('inf'),
            base_unit=t2_base, press_unit=t2_press,
            stop_loss=-(t2_base*10), profit_lock=t2_base*6, catastrophic_cap=-(t2_base*20)
        )
        
        # Tier 3 (High Roller)
        tiers[3] = TierConfig(
            level=3, min_ga=th_high, max_ga=float('inf'),
            base_unit=t3_base, press_unit=t3_press,
            stop_loss=-(t3_base*10), profit_lock=t3_base*6, catastrophic_cap=-(t3_base*20)
        )
        return tiers

    # --- FORTRESS LOGIC ---
    if mode == 'Fortress':
        # Flat betting only
        th_low = 1000.0 if game_type == 'Roulette' else 2000.0
        
        tiers[1] = TierConfig(
            level=1, min_ga=0, max_ga=th_low,
            base_unit=BASE_BET_T1, press_unit=BASE_BET_T1,
            stop_loss=-(BASE_BET_T1*10), profit_lock=BASE_BET_T1*6, catastrophic_cap=-(BASE_BET_T1*20)
        )
        tiers[2] = TierConfig(
            level=2, min_ga=th_low, max_ga=float('inf'),
            base_unit=BASE_BET_T1, press_unit=BASE_BET_T1, # No upgrade, just safety
            stop_loss=-(BASE_BET_T1*10), profit_lock=BASE_BET_T1*6, catastrophic_cap=-(BASE_BET_T1*20)
        )
        return tiers

    # --- STANDARD LOGIC (EXPONENTIAL) ---
    multipliers = [1, 2, 4, 10, 20, 40] 
    for i, mult in enumerate(multipliers):
        level = i + 1
        base = BASE_BET_T1 * mult
        min_ga = base * safety_factor
        max_ga = (BASE_BET_T1 * multipliers[i+1] * safety_factor) if i < len(multipliers)-1 else float('inf')
        
        tiers[level] = TierConfig(
            level=level, min_ga=min_ga, max_ga=max_ga,
            base_unit=base, press_unit=base,
            stop_loss=-(base * 10), profit_lock=base * 6, catastrophic_cap=-(base * 20)
        )
    return tiers

def get_tier_for_ga(current_ga: float, tier_map: dict = None, active_level: int = 1, mode: str = 'Standard', game_type: str = 'Baccarat') -> TierConfig:
    if tier_map is None:
        tier_map = generate_tier_map(mode=mode, game_type=game_type)

    if mode == 'Safe Titan':
        return tier_map[1]

    # --- TITAN HYSTERESIS ---
    if mode == 'Titan':
        th_low = 1000.0 if game_type == 'Roulette' else 2000.0
        th_high = 2500.0 if game_type == 'Roulette' else 5000.0
        th_drop = 2250.0 if game_type == 'Roulette' else 4500.0
        
        if active_level < 3:
            if current_ga >= th_high: return tier_map[3]
            if current_ga >= th_low: return tier_map[2]
            return tier_map[1] 
        if active_level == 3:
            if current_ga < th_drop: return tier_map[2]
            return tier_map[3]
        return tier_map[active_level] 

    # --- FORTRESS ---
    if mode == 'Fortress':
        th_low = 1000.0 if game_type == 'Roulette' else 2000.0
        if current_ga >= th_low: return tier_map[2]
        return tier_map[1]

    # --- STANDARD ---
    selected_tier = tier_map[min(tier_map.keys())]
    for level in sorted(tier_map.keys()):
        t = tier_map[level]
        if current_ga >= t.min_ga:
            selected_tier = t
        else:
            break
    return selected_tier
