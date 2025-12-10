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

# Base Params
BASE_BET_T1 = 50.0

def generate_tier_map(safety_factor: int = 25, max_tier_cap: int = 0) -> dict:
    """
    Generates the Tier Map.
    """
    tiers = {}
    
    # --- MODE A: PROTECTED BERSERKER (Toggle ON) ---
    if max_tier_cap == 2:
        # THRESHOLD: €2,000
        # If you have €2,000, you play €100. If you lose €1, you drop to €50.
        SAFETY_NET = 2000.0
        
        # Tier 1: Defense (€50)
        # Active from €0 to €1,999
        tiers[1] = TierConfig(
            level=1,
            min_ga=0,
            max_ga=SAFETY_NET,
            base_unit=50.0,
            press_unit=50.0,
            stop_loss=-(50.0 * 10),
            profit_lock=50.0 * 6,
            catastrophic_cap=-(50.0 * 20)
        )
        
        # Tier 2: Attack (€100)
        # Active from €2,000+
        tiers[2] = TierConfig(
            level=2,
            min_ga=SAFETY_NET,
            max_ga=float('inf'),
            base_unit=100.0,
            press_unit=100.0,
            stop_loss=-(100.0 * 10),
            profit_lock=100.0 * 6,
            catastrophic_cap=-(100.0 * 20)
        )
        return tiers

    # --- MODE B: STANDARD PROGRESSION (Toggle OFF) ---
    multipliers = [1, 2, 4, 10, 20, 40] 
    
    for i, mult in enumerate(multipliers):
        level = i + 1
        base = BASE_BET_T1 * mult
        min_ga = base * safety_factor
        
        is_last_tier = (i == len(multipliers) - 1)
        if is_last_tier:
            max_ga = float('inf')
        else:
            next_base = BASE_BET_T1 * multipliers[i+1]
            max_ga = next_base * safety_factor
            
        tiers[level] = TierConfig(
            level=level,
            min_ga=min_ga,
            max_ga=max_ga,
            base_unit=base,
            press_unit=base,
            stop_loss=-(base * 10),
            profit_lock=base * 6,
            catastrophic_cap=-(base * 20)
        )
        
    return tiers

def get_tier_for_ga(current_ga: float, tier_map: dict = None) -> TierConfig:
    if tier_map is None:
        tier_map = generate_tier_map()
    
    # Default to lowest
    selected_tier = tier_map[min(tier_map.keys())]
    
    for level in sorted(tier_map.keys()):
        t = tier_map[level]
        if current_ga >= t.min_ga:
            selected_tier = t
        else:
            break
            
    return selected_tier
