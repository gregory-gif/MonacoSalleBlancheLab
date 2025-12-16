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

# --- BETTING ENGINE MODES (MONACO EDITION: MIN €100) ---

def generate_tier_map(safety_factor: int = 25, mode: str = 'Standard') -> dict:
    tiers = {}
    
    # --- MODE: TITAN (Updated for €100 Min) ---
    if mode == 'Titan':
        # Tier 1: Defense (Below €2,000) -> Forced €100 (Monaco Minimum)
        tiers[1] = TierConfig(
            level=1, min_ga=0, max_ga=2000,
            base_unit=100.0, press_unit=100.0,
            stop_loss=-(100.0*10), profit_lock=100.0*6, catastrophic_cap=-(100.0*20)
        )
        # Tier 2: The Floor (Standard Play) -> €100 Base / €150 Press
        tiers[2] = TierConfig(
            level=2, min_ga=2000, max_ga=float('inf'),
            base_unit=100.0, press_unit=150.0, 
            stop_loss=-(100.0*10), profit_lock=100.0*6, catastrophic_cap=-(100.0*20)
        )
        # Tier 3: The Ceiling (High Roller) -> €150 Base / €250 Press
        tiers[3] = TierConfig(
            level=3, min_ga=5000, max_ga=float('inf'),
            base_unit=150.0, press_unit=250.0,
            stop_loss=-(150.0*10), profit_lock=150.0*6, catastrophic_cap=-(150.0*20)
        )
        return tiers

    # --- MODE: FORTRESS (Protected Berserker) ---
    if mode == 'Fortress':
        # There is no €50 safety anymore. It's €100 or bust.
        tiers[1] = TierConfig(
            level=1, min_ga=0, max_ga=2000,
            base_unit=100.0, press_unit=100.0,
            stop_loss=-(100.0*10), profit_lock=100.0*6, catastrophic_cap=-(100.0*20)
        )
        tiers[2] = TierConfig(
            level=2, min_ga=2000, max_ga=float('inf'),
            base_unit=100.0, press_unit=100.0, # Flat aggression
            stop_loss=-(100.0*10), profit_lock=100.0*6, catastrophic_cap=-(100.0*20)
        )
        return tiers

    # --- MODE: STANDARD (Exponential - Monaco Adjusted) ---
    # Old: 50 -> 100 -> 200
    # New: 100 -> 200 -> 400
    BASE_BET_T1 = 100.0 
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

def get_tier_for_ga(current_ga: float, tier_map: dict = None, active_level: int = 1, mode: str = 'Standard') -> TierConfig:
    if tier_map is None:
        tier_map = generate_tier_map()

    # --- TITAN HYSTERESIS LOGIC (Updated Thresholds) ---
    if mode == 'Titan':
        # 1. UPGRADE CHECK
        if active_level < 3:
            if current_ga >= 5000: return tier_map[3] # Cross 5k -> Tier 3
            if current_ga >= 2000: return tier_map[2] # Cross 2k -> Tier 2
            return tier_map[1] 

        # 2. DOWNGRADE CHECK (Sticky Safety)
        if active_level == 3:
            if current_ga < 4500: return tier_map[2] # Crash 4.5k -> Drop to 2
            return tier_map[3] # Stay at 3 
            
        return tier_map[active_level] 

    # --- FORTRESS LOGIC ---
    if mode == 'Fortress':
        if current_ga >= 2000: return tier_map[2]
        return tier_map[1]

    # --- STANDARD LOGIC ---
    selected_tier = tier_map[min(tier_map.keys())]
    for level in sorted(tier_map.keys()):
        t = tier_map[level]
        if current_ga >= t.min_ga:
            selected_tier = t
        else:
            break
    return selected_tier
