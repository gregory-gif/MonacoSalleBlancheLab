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

# --- HARD-WIRED FORTRESS CONFIGURATION ---
# No toggles. No multipliers. Just the "Sticky" Staircase.

def generate_tier_map(safety_factor: int = 0, max_tier_cap: int = 0) -> dict:
    """
    FORTRESS LOGIC (Hard-Wired):
    - Tier 2 (€100): ACTIVE if Bankroll >= €2,500
    - Tier 1 (€50):  ACTIVE if Bankroll < €2,500
    """
    tiers = {}
    
    # THRESHOLD: The "Hard Deck" is €2,500.
    STICKY_THRESHOLD = 2500.0
    
    # Tier 1: Defense Mode (€50)
    # Range: 0 to 2,499.99
    # This tier is active whenever you are below the Fortress walls.
    tiers[1] = TierConfig(
        level=1,
        min_ga=0,                 # Starts from 0
        max_ga=STICKY_THRESHOLD,  # Ends at 2500
        base_unit=50.0,
        press_unit=50.0,
        stop_loss=-(50.0 * 10),      # -€500
        profit_lock=50.0 * 6,        # +€300 (Default)
        catastrophic_cap=-(50.0 * 20) # -€1000
    )
    
    # Tier 2: Cruising Mode (€100)
    # Range: 2,500 to Infinity
    # This tier is forced active as long as you have the cash.
    tiers[2] = TierConfig(
        level=2,
        min_ga=STICKY_THRESHOLD,  # Starts at 2500
        max_ga=float('inf'),      # Never ends
        base_unit=100.0,
        press_unit=100.0,
        stop_loss=-(100.0 * 10),     # -€1000
        profit_lock=100.0 * 6,       # +€600 (Default)
        catastrophic_cap=-(100.0 * 20)# -€2000
    )
    
    return tiers

def get_tier_for_ga(current_ga: float, tier_map: dict = None) -> TierConfig:
    """
    Selects the tier based on the Hard-Wired Fortress Map.
    """
    if tier_map is None:
        tier_map = generate_tier_map()
        
    # Default to Tier 1 (Defense)
    selected_tier = tier_map[1]
    
    # Check if we qualify for Tier 2 (Cruising)
    # Since we only have 2 tiers, we just check the higher one.
    t2 = tier_map[2]
    if current_ga >= t2.min_ga:
        selected_tier = t2
            
    return selected_tier
