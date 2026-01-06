"""
Monaco Salle Blanche Lab - Spice System v5.0
==============================================
Advanced sector betting system for roulette with dynamic triggers,
family-based constraints, and momentum-driven target profit adjustments.

Spices = Optional one-shot sector bets (Tiers, Voisins, Zéro, etc.)
layered on top of baseline Crossfire gameplay.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, List
import random


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

class SpiceFamily(Enum):
    """Three-tier spice family hierarchy"""
    A_LIGHT = "A_LIGHT"          # Low risk, frequent
    B_MEDIUM = "B_MEDIUM"        # Medium sector bets
    C_PRESTIGE = "C_PRESTIGE"    # High-power VIP bets


class SpiceType(Enum):
    """Seven distinct spice bet types"""
    ZERO_LEGER = "ZERO_LEGER"
    JEU_ZERO = "JEU_ZERO"
    ZERO_CROWN = "ZERO_CROWN"
    TIERS = "TIERS"
    ORPHELINS = "ORPHELINS"
    ORPHELINS_PLEIN = "ORPHELINS_PLEIN"
    VOISINS = "VOISINS"


# ============================================================================
# CONFIGURATION STRUCTURES
# ============================================================================

@dataclass
class SpiceRule:
    """Configuration for a single spice type - fully tunable by user"""
    enabled: bool
    family: SpiceFamily
    
    # TUNABLE BY USER
    trigger_pl_units: float          # when P/L >= this, spice can fire
    max_uses_per_session: int        # per spice
    cooldown_spins: int              # min spins between uses
    
    # Optional overrides
    min_pl_units: Optional[float] = None     # lower bound of profit window
    max_pl_units: Optional[float] = None     # upper bound of profit window
    
    # Constant structural bits
    unit_bet_size_eur: float = 10.0          # € per chip (usually table min)
    pattern_id: str = ""                     # mapping to bet layout


@dataclass
class GlobalSpiceConfig:
    """Global constraints across all spice families"""
    max_total_spices_per_session: int = 3    # GLOBAL CAP (tunable)
    max_spices_per_spin: int = 1             # usually 1, tunable for experiments
    disable_if_caroline_step4: bool = True   # safety toggle
    disable_if_pl_below_zero: bool = True    # optional safety


@dataclass
class SpiceState:
    """Runtime state tracking for spice system"""
    global_spice_count: int = 0              # Total spices used this session
    spices_this_spin: int = 0                # Spices fired this spin (reset each spin)
    
    # Per-spice tracking
    used_this_session: Dict[str, int] = field(default_factory=dict)
    last_used_spin: Dict[str, Optional[int]] = field(default_factory=dict)
    cooldown_remaining: Dict[str, int] = field(default_factory=dict)
    
    # Statistics
    spice_wins: int = 0
    spice_losses: int = 0
    spice_total_cost: float = 0.0
    spice_total_payout: float = 0.0
    momentum_tp_gains: float = 0.0
    
    # Distribution tracking
    spice_usage_by_type: Dict[str, int] = field(default_factory=dict)


@dataclass
class SpicePattern:
    """Defines the actual roulette bet structure for a spice"""
    pattern_id: str
    spice_type: SpiceType
    unit_cost: int                           # Total number of units (chips) required
    numbers_covered: List[int]               # All winning numbers
    bet_structure: Dict[str, any]            # Detailed bet layout with chip counts
    # bet_structure format: {"straight_up": [(number, chips)], "splits": [([n1,n2], chips)], ...}


# ============================================================================
# BET PATTERN DEFINITIONS
# ============================================================================

SPICE_PATTERNS: Dict[str, SpicePattern] = {
    "ZERO_LEGER_PATTERN": SpicePattern(
        pattern_id="ZERO_LEGER_PATTERN",
        spice_type=SpiceType.ZERO_LEGER,
        unit_cost=3,
        numbers_covered=[0, 3, 12, 15, 26, 32, 35],
        bet_structure={
            "straight_up": [(26, 1)],  # (number, chips)
            "splits": [([0, 3], 1), ([12, 15], 1), ([32, 35], 1)]  # (numbers, chips)
        }
    ),
    
    "JEU_ZERO_PATTERN": SpicePattern(
        pattern_id="JEU_ZERO_PATTERN",
        spice_type=SpiceType.JEU_ZERO,
        unit_cost=4,
        numbers_covered=[0, 3, 12, 15, 26, 32, 35],
        bet_structure={
            "straight_up": [(26, 1)],
            "splits": [([0, 3], 1), ([12, 15], 1), ([32, 35], 1)]
        }
    ),
    
    "ZERO_CROWN_PATTERN": SpicePattern(
        pattern_id="ZERO_CROWN_PATTERN",
        spice_type=SpiceType.ZERO_CROWN,
        unit_cost=4,
        numbers_covered=[0, 3, 12, 15, 19, 26, 32, 35],
        bet_structure={
            "straight_up": [(26, 1)],
            "splits": [([0, 3], 1), ([12, 15], 1), ([32, 35], 1), ([19, 22], 1)]
        }
    ),
    
    "TIERS_PATTERN": SpicePattern(
        pattern_id="TIERS_PATTERN",
        spice_type=SpiceType.TIERS,
        unit_cost=6,
        numbers_covered=[5, 8, 10, 11, 13, 16, 23, 24, 27, 30, 33, 36],
        bet_structure={
            "splits": [([5, 8], 1), ([10, 11], 1), ([13, 16], 1), ([23, 24], 1), ([27, 30], 1), ([33, 36], 1)]
        }
    ),
    
    "ORPHELINS_PATTERN": SpicePattern(
        pattern_id="ORPHELINS_PATTERN",
        spice_type=SpiceType.ORPHELINS,
        unit_cost=5,
        numbers_covered=[1, 6, 9, 14, 17, 20, 31, 34],
        bet_structure={
            "straight_up": [(1, 1)],
            "splits": [([6, 9], 1), ([14, 17], 1), ([17, 20], 1), ([31, 34], 1)]
        }
    ),
    
    "ORPHELINS_PLEIN_PATTERN": SpicePattern(
        pattern_id="ORPHELINS_PLEIN_PATTERN",
        spice_type=SpiceType.ORPHELINS_PLEIN,
        unit_cost=8,
        numbers_covered=[1, 6, 9, 14, 17, 20, 31, 34],
        bet_structure={
            "straight_up": [(1, 1), (6, 1), (9, 1), (14, 1), (17, 1), (20, 1), (31, 1), (34, 1)]
        }
    ),
    
    "VOISINS_PATTERN": SpicePattern(
        pattern_id="VOISINS_PATTERN",
        spice_type=SpiceType.VOISINS,
        unit_cost=9,
        numbers_covered=[0, 2, 3, 4, 7, 12, 15, 18, 19, 21, 22, 25, 26, 28, 29, 32, 35],
        bet_structure={
            "trio": [([0, 2, 3], 2)],  # 2 chips on trio
            "corners": [([25, 26, 28, 29], 2)],  # 2 chips on corner
            "splits": [([4, 7], 1), ([12, 15], 1), ([18, 21], 1), ([19, 22], 1), ([32, 35], 1)]  # 1 chip each
        }
    ),
}


# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

DEFAULT_SPICE_CONFIG: Dict[SpiceType, SpiceRule] = {
    SpiceType.ZERO_LEGER: SpiceRule(
        enabled=True,
        family=SpiceFamily.A_LIGHT,
        trigger_pl_units=15,
        max_uses_per_session=2,
        cooldown_spins=5,
        min_pl_units=15,
        max_pl_units=80,
        unit_bet_size_eur=10,
        pattern_id="ZERO_LEGER_PATTERN",
    ),
    SpiceType.JEU_ZERO: SpiceRule(
        enabled=True,
        family=SpiceFamily.A_LIGHT,
        trigger_pl_units=15,
        max_uses_per_session=2,
        cooldown_spins=5,
        min_pl_units=15,
        max_pl_units=80,
        unit_bet_size_eur=10,
        pattern_id="JEU_ZERO_PATTERN",
    ),
    SpiceType.ZERO_CROWN: SpiceRule(
        enabled=True,
        family=SpiceFamily.A_LIGHT,
        trigger_pl_units=15,
        max_uses_per_session=2,
        cooldown_spins=5,
        min_pl_units=15,
        max_pl_units=80,
        unit_bet_size_eur=10,
        pattern_id="ZERO_CROWN_PATTERN",
    ),
    SpiceType.TIERS: SpiceRule(
        enabled=True,
        family=SpiceFamily.B_MEDIUM,
        trigger_pl_units=25,
        max_uses_per_session=1,
        cooldown_spins=8,
        min_pl_units=25,
        max_pl_units=80,
        unit_bet_size_eur=10,
        pattern_id="TIERS_PATTERN",
    ),
    SpiceType.ORPHELINS: SpiceRule(
        enabled=True,
        family=SpiceFamily.B_MEDIUM,
        trigger_pl_units=25,
        max_uses_per_session=1,
        cooldown_spins=8,
        min_pl_units=25,
        max_pl_units=80,
        unit_bet_size_eur=10,
        pattern_id="ORPHELINS_PATTERN",
    ),
    SpiceType.ORPHELINS_PLEIN: SpiceRule(
        enabled=True,
        family=SpiceFamily.C_PRESTIGE,
        trigger_pl_units=35,
        max_uses_per_session=1,
        cooldown_spins=10,
        min_pl_units=35,
        max_pl_units=100,
        unit_bet_size_eur=10,
        pattern_id="ORPHELINS_PLEIN_PATTERN",
    ),
    SpiceType.VOISINS: SpiceRule(
        enabled=True,
        family=SpiceFamily.C_PRESTIGE,
        trigger_pl_units=35,
        max_uses_per_session=1,
        cooldown_spins=10,
        min_pl_units=35,
        max_pl_units=100,
        unit_bet_size_eur=10,
        pattern_id="VOISINS_PATTERN",
    ),
}

DEFAULT_GLOBAL_SPICE_CONFIG = GlobalSpiceConfig(
    max_total_spices_per_session=3,
    max_spices_per_spin=1,
    disable_if_caroline_step4=True,
    disable_if_pl_below_zero=True,
)


# ============================================================================
# CORE SPICE ENGINE
# ============================================================================

class SpiceEngine:
    """Main spice evaluation and execution engine"""
    
    def __init__(
        self,
        spice_config: Dict[SpiceType, SpiceRule],
        global_config: GlobalSpiceConfig,
        unit_ratio: float = 1.0
    ):
        self.spice_config = spice_config
        self.global_config = global_config
        self.unit_ratio = unit_ratio  # Hybrid mode: 1.0 = standard, 0.5 = half units
        self.state = SpiceState()
        
        # Initialize tracking dictionaries
        for spice_type in SpiceType:
            pattern_id = spice_config[spice_type].pattern_id
            self.state.used_this_session[pattern_id] = 0
            self.state.last_used_spin[pattern_id] = None
            self.state.cooldown_remaining[pattern_id] = 0
            self.state.spice_usage_by_type[spice_type.value] = 0
    
    def reset_session(self):
        """Reset state for a new session"""
        self.state = SpiceState()
        for spice_type in SpiceType:
            pattern_id = self.spice_config[spice_type].pattern_id
            self.state.used_this_session[pattern_id] = 0
            self.state.last_used_spin[pattern_id] = None
            self.state.cooldown_remaining[pattern_id] = 0
            self.state.spice_usage_by_type[spice_type.value] = 0
    
    def reset_spin(self):
        """Reset per-spin counters (call at start of each spin)"""
        self.state.spices_this_spin = 0
    
    def can_fire_spice(
        self,
        spice: SpiceRule,
        session_pl_units: float,
        spin_index: int,
        caroline_at_step4: bool,
        session_start_bankroll: float,
        current_bankroll: float,
        stop_loss: float
    ) -> bool:
        """
        Determine if a spice can be fired based on all constraints.
        
        Args:
            spice: The spice rule to check
            session_pl_units: Current session P/L in units
            spin_index: Current spin number (1-indexed)
            caroline_at_step4: Whether Caroline is at step 4 (40€ level)
            session_start_bankroll: Starting bankroll for this session
            current_bankroll: Current bankroll
            stop_loss: Stop loss threshold
            
        Returns:
            True if spice can fire, False otherwise
        """
        # Check if enabled
        if not spice.enabled:
            return False
        
        # Check global spice cap
        if self.state.global_spice_count >= self.global_config.max_total_spices_per_session:
            return False
        
        # Check max spices per spin
        if self.state.spices_this_spin >= self.global_config.max_spices_per_spin:
            return False
        
        # Check per-spice max uses
        if (spice.max_uses_per_session > 0 and 
            self.state.used_this_session[spice.pattern_id] >= spice.max_uses_per_session):
            return False
        
        # CAROLINE SAFETY CHECK
        if self.global_config.disable_if_caroline_step4 and caroline_at_step4:
            return False
        
        # STOP LOSS LOCKOUT
        if current_bankroll <= (session_start_bankroll - stop_loss):
            return False
        
        # Check if PL is negative (optional safety)
        if self.global_config.disable_if_pl_below_zero and session_pl_units < 0:
            return False
        
        # Check trigger threshold
        if session_pl_units < spice.trigger_pl_units:
            return False
        
        # Check profit window bounds
        if spice.min_pl_units is not None and session_pl_units < spice.min_pl_units:
            return False
        
        if spice.max_pl_units is not None and session_pl_units > spice.max_pl_units:
            return False
        
        # Check cooldown
        last_spin = self.state.last_used_spin[spice.pattern_id]
        if last_spin is not None and (spin_index - last_spin) < spice.cooldown_spins:
            return False
        
        return True
    
    def evaluate_and_fire_spice(
        self,
        session_pl_units: float,
        spin_index: int,
        caroline_at_step4: bool,
        session_start_bankroll: float,
        current_bankroll: float,
        stop_loss: float
    ) -> Optional[SpiceType]:
        """
        Evaluate all spices and fire the first eligible one.
        
        Returns:
            SpiceType if a spice was fired, None otherwise
        """
        # Try each spice type in priority order
        for spice_type in SpiceType:
            spice = self.spice_config[spice_type]
            
            if self.can_fire_spice(
                spice,
                session_pl_units,
                spin_index,
                caroline_at_step4,
                session_start_bankroll,
                current_bankroll,
                stop_loss
            ):
                # Fire this spice!
                self._fire_spice(spice_type, spice, spin_index)
                return spice_type
        
        return None
    
    def _fire_spice(self, spice_type: SpiceType, spice: SpiceRule, spin_index: int):
        """Internal: Execute spice firing and update counters"""
        pattern_id = spice.pattern_id
        
        # Update counters
        self.state.used_this_session[pattern_id] += 1
        self.state.last_used_spin[pattern_id] = spin_index
        self.state.global_spice_count += 1
        self.state.spices_this_spin += 1
        self.state.spice_usage_by_type[spice_type.value] += 1
        
        # Track cost (apply unit ratio for hybrid mode)
        pattern = SPICE_PATTERNS[pattern_id]
        cost = pattern.unit_cost * spice.unit_bet_size_eur * self.unit_ratio
        self.state.spice_total_cost += cost
    
    def resolve_spice(
        self,
        spice_type: SpiceType,
        number: int,
        unit_bet_size: float
    ) -> tuple[float, bool]:
        """
        Calculate payout for a spice bet given the winning number.
        
        CRITICAL: Correctly handles:
        1. Overlapping coverage (e.g., Orphelins #17 covered by 2 splits)
        2. Multi-chip bets (e.g., Voisins trio uses 2 chips)
        3. NO la partage on inside bets (2.70% edge, not 1.35%)
        
        Each winning chip pays out independently.
        
        Args:
            spice_type: The spice that was fired
            number: The winning roulette number (0-36)
            unit_bet_size: The bet size per unit in euros
            
        Returns:
            (net_pnl, won) - Net P/L and whether it was a win
        """
        spice = self.spice_config[spice_type]
        pattern = SPICE_PATTERNS[spice.pattern_id]
        
        # Calculate total cost (all chips placed)
        cost = pattern.unit_cost * unit_bet_size * self.unit_ratio
        
        # Calculate payout by checking ALL bet placements
        # CRITICAL: Must handle overlapping coverage and multi-chip bets
        total_payout = 0.0
        winning_chips = 0
        
        bet_structure = pattern.bet_structure
        chip_size = unit_bet_size * self.unit_ratio
        
        # Check straight-ups: (number, chip_count)
        if "straight_up" in bet_structure:
            for num, chips in bet_structure["straight_up"]:
                if num == number:
                    # Straight up pays 35:1 per chip + stake returned
                    # Example: 1 chip @ €10 wins → €10×35 + €10 = €360
                    total_payout += chips * ((chip_size * 35) + chip_size)
                    winning_chips += chips
        
        # Check splits: ([n1, n2], chip_count)
        if "splits" in bet_structure:
            for nums, chips in bet_structure["splits"]:
                if number in nums:
                    # Split pays 17:1 per chip + stake
                    total_payout += chips * ((chip_size * 17) + chip_size)
                    winning_chips += chips
        
        # Check corners: ([n1, n2, n3, n4], chip_count)
        if "corners" in bet_structure:
            for nums, chips in bet_structure["corners"]:
                if number in nums:
                    # Corner pays 8:1 per chip + stake
                    total_payout += chips * ((chip_size * 8) + chip_size)
                    winning_chips += chips
        
        # Check trio: ([n1, n2, n3], chip_count)
        if "trio" in bet_structure:
            for nums, chips in bet_structure["trio"]:
                if number in nums:
                    # Trio pays 11:1 per chip + stake
                    total_payout += chips * ((chip_size * 11) + chip_size)
                    winning_chips += chips
        
        net_pnl = total_payout - cost
        won = winning_chips > 0
        
        # Update statistics
        if won:
            self.state.spice_wins += 1
        else:
            self.state.spice_losses += 1
        
        self.state.spice_total_payout += total_payout
        
        return net_pnl, won
    
    def apply_momentum_tp_boost(
        self,
        spice_type: SpiceType,
        current_tp: float,
        unit_size: float
    ) -> float:
        """
        Apply momentum TP increase on spice win.
        
        Args:
            spice_type: The spice that won
            current_tp: Current target profit
            unit_size: Base unit size
            
        Returns:
            New target profit
        """
        spice = self.spice_config[spice_type]
        
        if spice.family == SpiceFamily.C_PRESTIGE:
            boost = 40 * unit_size
        else:
            boost = 20 * unit_size
        
        self.state.momentum_tp_gains += boost
        return current_tp + boost
    
    def get_statistics(self) -> Dict:
        """Return comprehensive statistics for the session"""
        hit_rate = 0.0
        if (self.state.spice_wins + self.state.spice_losses) > 0:
            hit_rate = self.state.spice_wins / (self.state.spice_wins + self.state.spice_losses)
        
        avg_cost = 0.0
        if self.state.global_spice_count > 0:
            avg_cost = self.state.spice_total_cost / self.state.global_spice_count
        
        return {
            "total_spices_used": self.state.global_spice_count,
            "spice_wins": self.state.spice_wins,
            "spice_losses": self.state.spice_losses,
            "hit_rate": hit_rate,
            "total_cost": self.state.spice_total_cost,
            "total_payout": self.state.spice_total_payout,
            "net_spice_pl": self.state.spice_total_payout - self.state.spice_total_cost,
            "avg_cost_per_spice": avg_cost,
            "momentum_tp_gains": self.state.momentum_tp_gains,
            "distribution": self.state.spice_usage_by_type.copy(),
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_default_engine() -> SpiceEngine:
    """Create a spice engine with default configuration"""
    return SpiceEngine(DEFAULT_SPICE_CONFIG, DEFAULT_GLOBAL_SPICE_CONFIG)


def create_custom_engine(
    spice_config: Dict[SpiceType, SpiceRule],
    global_config: GlobalSpiceConfig
) -> SpiceEngine:
    """Create a spice engine with custom configuration"""
    return SpiceEngine(spice_config, global_config)
