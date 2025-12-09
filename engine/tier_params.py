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
    
    If max_tier_cap == 2, we activate 'FORTRESS HYSTERESIS':
    - Tier 2 (€100) is ACTIVE as long as Bankroll >= €2,500.
    - We only drop to Tier 1 (€50) if we fall below €2,500.
    - Insolvency (<1000) handled by simulator loop check.
    """
    tiers = {}
    
    # --- FORTRESS LOGIC (Sticky Tiers) ---
    if max_tier_cap == 2:
        # THRESHOLD: The "Hard Deck" is €2,500.
        STICKY_THRESHOLD = 2500.0
        
        # Tier 1: Defense Mode (€50)
        # Range: 0 to 2,499
        tiers[1] = TierConfig(
            level=1,
            min_ga=0,
            max_ga=STICKY_THRESHOLD, 
            base_unit=50.0,
            press_unit=50.0,
            stop_loss=-(50.0 * 10),
            profit_lock=50.0 * 6,
            catastrophic_cap=-(50.0 * 20)
        )
        
        # Tier 2: Cruising Mode (€100)
        # Range: 2,500 to Infinity
        # Note: This overrides linear safety. Even if you have €2,501 and Safety is 50x
        # (which usually requires €5,000), this forces the €100 bet.
        tiers[2] = TierConfig(
            level=2,
            min_ga=STICKY_THRESHOLD,
            max_ga=float('inf'),
            base_unit=100.0,
            press_unit=100.0,
            stop_loss=-(100.0 * 10),
            profit_lock=100.0 * 6,
            catastrophic_cap=-(100.0 * 20)
        )
        return tiers

    # --- STANDARD LINEAR MATH (Exponential Growth) ---
    # Only used if Cap is OFF
    multipliers = [1, 2, 4, 10, 20, 40] 
    
    for i, mult in enumerate(multipliers):
        level = i + 1
        base = BASE_BET_T1 * mult
        
        # Linear Safety: Min GA = Base * Safety Factor
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
