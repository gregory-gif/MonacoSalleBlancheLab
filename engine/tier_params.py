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

def generate_tier_map(safety_factor: int, max_tier_cap: int = 0) -> dict:
    """
    Generates the Tier Map.
    if max_tier_cap == 2 (Fortress Mode):
       - GA >= 2000: Bet €100 (CRUISING)
       - GA < 2000:  Bet €50  (DEFENSE)
    """
    tiers = {}
    
    # --- FORTRESS LOGIC (Hard Override) ---
    if max_tier_cap == 2:
        # THRESHOLD ADJUSTED: 2000 (Matches Start GA)
        CRUISE_ALTITUDE = 2000.0
        
        # Tier 1: €50 Bet (Defense Mode)
        tiers[1] = TierConfig(
            level=1,
            min_ga=0,
            max_ga=CRUISE_ALTITUDE, 
            base_unit=50.0,
            press_unit=50.0,
            stop_loss=-(50.0 * 10),
            profit_lock=50.0 * 6,
            catastrophic_cap=-(50.0 * 20)
        )
        
        # Tier 2: €100 Bet (Cruising Mode)
        tiers[2] = TierConfig(
            level=2,
            min_ga=CRUISE_ALTITUDE,
            max_ga=float('inf'),
            base_unit=100.0,
            press_unit=100.0,
            stop_loss=-(100.0 * 10),
            profit_lock=100.0 * 6,
            catastrophic_cap=-(100.0 * 20)
        )
        return tiers

    # --- STANDARD MATH LOGIC (Exponential) ---
    multipliers = [1, 2, 4, 10, 20, 40] 
    
    for i, mult in enumerate(multipliers):
        level = i + 1
        base = BASE_BET_T1 * mult
        
        # Standard safety calc
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
    """Returns the appropriate TierConfig for a given Bankroll."""
    if tier_map is None:
        tier_map = generate_tier_map(25)
        
    # Default to lowest
    selected_tier = tier_map[min(tier_map.keys())]
    
    # Iterate to find active tier
    for level in sorted(tier_map.keys()):
        t = tier_map[level]
        if current_ga >= t.min_ga:
            selected_tier = t
        else:
            break
            
    return selected_tier
