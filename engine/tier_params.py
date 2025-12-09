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
    Generates the Tier Map based on Safety Factor (Buffer).
    max_tier_cap: If > 0, stops generating tiers at this level (e.g. 2 = Max Tier 2).
    """
    tiers = {}
    current_base = BASE_BET_T1
    
    # We define up to Tier 6 standard, but the loop can handle logic
    # Tiers: 1=50, 2=100, 3=200, 4=500, 5=1000, 6=2000
    multipliers = [1, 2, 4, 10, 20, 40] 
    
    for i, mult in enumerate(multipliers):
        level = i + 1
        
        # If a cap is set and we passed it, stop.
        if max_tier_cap > 0 and level > max_tier_cap:
            break
            
        base = BASE_BET_T1 * mult
        
        # Min GA = Base * Safety Factor
        min_ga = base * safety_factor
        
        # Logic to determine Max GA for this tier (it's the Min GA of the next tier)
        # If this is the LAST tier (either by natural end or CAP), Max GA is infinity
        is_last_tier = (i == len(multipliers) - 1) or (max_tier_cap > 0 and level == max_tier_cap)
        
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
            press_unit=base, # Standard Press is 1 unit
            stop_loss=-(base * 10),
            profit_lock=base * 6, # Default, overriden by overrides
            catastrophic_cap=-(base * 20)
        )
        
    return tiers

def get_tier_for_ga(current_ga: float, tier_map: dict = None) -> TierConfig:
    """
    Returns the appropriate TierConfig for a given Bankroll.
    """
    if tier_map is None:
        # Default safety of 25 if not provided (shouldn't happen in sim)
        tier_map = generate_tier_map(25)
        
    # Find the highest tier where current_ga >= min_ga
    selected_tier = tier_map[1] # Default to Tier 1
    
    for level in sorted(tier_map.keys()):
        t = tier_map[level]
        if current_ga >= t.min_ga:
            selected_tier = t
        else:
            break
            
    return selected_tier
