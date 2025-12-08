from dataclasses import dataclass

# ==========================================
# ⚙️ GLOBAL ECOSYSTEM CONFIGURATION
# ==========================================

# 4. Financial Defense Constants
INSOLVENCY_FLOOR = 1000.0       # STOP YEAR if GA drops below this
REBUILD_THRESHOLD = 1500.0      # Resume play only when GA reaches this
CONTRIBUTION_NORMAL = 300.0     # Monthly add-on if PnL is positive/neutral
CONTRIBUTION_DEFENSIVE = 200.0  # Monthly add-on if Lifetime PnL is negative

# 6. Luxury Tax Constants
LUXURY_TAX_THRESHOLD = 12500.0  # Cap for wealth accumulation
LUXURY_TAX_RATE = 0.25          # 25% tax on surplus

@dataclass
class YearState:
    """
    Tracks the financial health of the current year.
    """
    ga_start: float      # GA0: Starting Bankroll for the year
    contributions: float # C: Total added cash (Monthly savings)
    play_pnl: float      # Net result from Baccarat sessions
    luxury_tax: float    # LT: Tax paid on surplus
    
    @property
    def current_ga(self) -> float:
        """Current Games Account Balance"""
        return self.ga_start + self.contributions + self.play_pnl - self.luxury_tax

    @property
    def ytd_pnl(self) -> float:
        """Year-to-Date Profit/Loss (including tax impact)"""
        return self.play_pnl - self.luxury_tax

def calculate_monthly_contribution(lifetime_pnl: float) -> float:
    """
    Determines the monthly contribution based on financial performance.
    - €300/mo normally.
    - €200/mo if negative lifetime PnL (tightening the belt).
    """
    if lifetime_pnl < 0:
        return CONTRIBUTION_DEFENSIVE
    return CONTRIBUTION_NORMAL

def calculate_luxury_tax(ga: float) -> float:
    """
    Calculates the Luxury Tax if GA exceeds the threshold.
    Returns the tax amount (does not deduct it).
    """
    if ga > LUXURY_TAX_THRESHOLD:
        surplus = ga - LUXURY_TAX_THRESHOLD
        return surplus * LUXURY_TAX_RATE
    return 0.0

def check_insolvency(ga: float) -> bool:
    """
    Checks if the Games Account has breached the insolvency floor.
    """
    return ga < INSOLVENCY_FLOOR

def can_resume_play(ga: float) -> bool:
    """
    Checks if the GA has rebuilt enough to resume operations after insolvency.
    """
    return ga >= REBUILD_THRESHOLD
