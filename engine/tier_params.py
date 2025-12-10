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
    Generates the Tier Map based on the Toggle Switch.
    """
    tiers = {}
    
    # --- MODE A: BERSERKER (Toggle ON) ---
    # Goal: Force €100 bets from the start to hit Gold Volume.
    if max_tier_cap == 2:
        tiers[1] = TierConfig(
            level=2,  # Label as Tier 2
            min_ga=0, # Active immediately (No €2,500 waiting room)
            max_ga=float('inf'),
            base_unit=100.0,
            press_unit=100.0,
            stop_loss=-(100.0 * 10),
            profit_lock=100.0 * 6,
            catastrophic_cap=-(100.0 * 20)
        )
        return tiers

    # --- MODE B: STANDARD PROGRESSION (Toggle OFF) ---
    # Goal: Safe, exponential growth from €50 up to €2,000+.
    multipliers = [1, 2, 4, 10, 20, 40] 
    
    for i, mult in enumerate(multipliers):
        level = i + 1
        base = BASE_BET_T1 * mult
        
        # Standard Linear Safety (e.g., 50 * 30 = 1500 to start)
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
    """
    Returns the appropriate TierConfig for a given Bankroll.
    """
    if tier_map is None:
        tier_map = generate_tier_map()
        
    # If using Berserker Mode (Map has only 1 entry), return it immediately.
    if len(tier_map) == 1:
        return tier_map[list(tier_map.keys())[0]]
    
    # Otherwise, use standard logic to find the right tier for current_ga
    selected_tier = tier_map[min(tier_map.keys())]
    
    for level in sorted(tier_map.keys()):
        t = tier_map[level]
        if current_ga >= t.min_ga:
            selected_tier = t
        else:
            break
            
    return selected_tier
