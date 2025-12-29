"""
Monaco Salle Blanche Lab - Dynamic Doctrine Engine v1.0
========================================================
State-driven betting system that automatically switches between:
- PLATINUM Doctrine (standard evening gameplay)
- TIGHT Doctrine (after losing session or deep drawdown)
- COOL_OFF Mode (bankroll safety mode)

All thresholds, durations, stop-losses, and targets are configurable.
Enables A/B testing of recovery behaviors while maintaining bankroll safety.
"""

from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# CORE DATA STRUCTURES
# ============================================================================

@dataclass
class DoctrineConfig:
    """
    Betting rules for a specific doctrine.
    All values are configurable - no hard-coded constants.
    """
    stop_loss_u: float          # Stop-loss in units (e.g., 10)
    target_u: float             # Profit target in units (e.g., 10)
    press_wins: int             # Consecutive wins to trigger press (e.g., 3)
    press_depth: int            # Max press depth (e.g., 3 or 999 for unlimited)
    iron_gate: int              # Max consecutive losing hands before retreat (e.g., 3)


@dataclass
class DoctrineStateRules:
    """
    State transition logic configuration.
    Controls when the system switches between doctrines.
    All thresholds are variable and UI-controlled.
    """
    # Triggers for entering TIGHT mode from PLATINUM
    loss_trigger_pl_u: float             # Single Platinum loss > this triggers TIGHT (units)
    drawdown_trigger_pct: float          # Drawdown % from peak that triggers TIGHT (e.g., 0.15)
    drawdown_trigger_eur: float          # Absolute drawdown € trigger (0 = disabled)
    
    # TIGHT doctrine session limits
    tight_min_sessions: int              # Minimum TIGHT sessions before recovery check
    tight_max_sessions: int              # Maximum TIGHT sessions before COOL_OFF
    
    # COOL_OFF configuration
    cooloff_enabled: bool                # Enable cool-off mode
    cooloff_ga_floor: float              # Bankroll floor for insolvency (€)
    cooloff_min_months: int              # Minimum months in cool-off
    cooloff_recovery_drawdown_pct: float # Drawdown % threshold for recovery (e.g., 0.07)
    
    # Roulette coupling
    link_roulette_to_state: bool         # Whether roulette follows doctrine state
    roulette_scale_platinum: float       # Roulette stake multiplier in PLATINUM (e.g., 1.0)
    roulette_scale_tight: float          # Roulette stake multiplier in TIGHT (e.g., 0.5)
    roulette_scale_cooloff: float        # Roulette stake multiplier in COOL_OFF (e.g., 0.0)


@dataclass
class DoctrineContext:
    """
    Runtime state tracking for the doctrine engine.
    Maintains current state and extended memory across sessions.
    """
    state: str = "PLATINUM"              # Current doctrine: "PLATINUM" | "TIGHT" | "COOL_OFF"
    GA_current: float = 0.0              # Current bankroll
    GA_peak: float = 0.0                 # Peak bankroll achieved
    last_result_u: float = 0.0           # Last session result in units
    tight_sessions_done: int = 0         # Counter for TIGHT sessions completed
    cooloff_months_done: int = 0         # Counter for months in COOL_OFF
    
    # Statistics
    total_sessions: int = 0
    platinum_sessions: int = 0
    tight_sessions: int = 0
    cooloff_months: int = 0
    transitions: list = field(default_factory=list)  # History of state changes


# ============================================================================
# STATE TRANSITION LOGIC (MAIN ENGINE)
# ============================================================================

def choose_state_for_next_session(ctx: DoctrineContext, rules: DoctrineStateRules) -> str:
    """
    Determine which doctrine to use for the next session.
    Implements the complete state machine logic with all trigger conditions.
    
    Args:
        ctx: Current doctrine context with state and memory
        rules: Configuration rules for state transitions
        
    Returns:
        Next state: "PLATINUM" | "TIGHT" | "COOL_OFF"
    """
    GA_cur = ctx.GA_current
    GA_peak = ctx.GA_peak or GA_cur
    dd_eur = GA_peak - GA_cur
    dd_pct = dd_eur / GA_peak if GA_peak > 0 else 0
    
    # Insolvency check
    insolvent = rules.cooloff_enabled and GA_cur < rules.cooloff_ga_floor
    
    # Red-zone trigger conditions
    in_red_zone = (
        dd_pct >= rules.drawdown_trigger_pct or
        (rules.drawdown_trigger_eur > 0 and dd_eur >= rules.drawdown_trigger_eur) or
        (ctx.state == "PLATINUM" and ctx.last_result_u <= -rules.loss_trigger_pl_u)
    )
    
    # === PLATINUM → ? ===
    if ctx.state == "PLATINUM":
        if insolvent:
            return "COOL_OFF"
        if in_red_zone:
            ctx.tight_sessions_done = 0
            return "TIGHT"
        return "PLATINUM"
    
    # === TIGHT → ? ===
    if ctx.state == "TIGHT":
        finished_min = ctx.tight_sessions_done >= rules.tight_min_sessions
        finished_max = ctx.tight_sessions_done >= rules.tight_max_sessions
        recovered = dd_pct < rules.cooloff_recovery_drawdown_pct
        
        if insolvent:
            return "COOL_OFF"
        
        if finished_max and in_red_zone and rules.cooloff_enabled:
            return "COOL_OFF"
        
        if finished_min and recovered:
            return "PLATINUM"
        
        return "TIGHT"
    
    # === COOL_OFF → ? ===
    if ctx.state == "COOL_OFF":
        if not rules.cooloff_enabled:
            return "PLATINUM"
        
        recovered = (
            GA_cur >= rules.cooloff_ga_floor and
            dd_pct < rules.cooloff_recovery_drawdown_pct
        )
        served_time = ctx.cooloff_months_done >= rules.cooloff_min_months
        
        if recovered and served_time:
            ctx.tight_sessions_done = 0
            ctx.cooloff_months_done = 0
            return "PLATINUM"
        
        return "COOL_OFF"
    
    # Fallback (should never reach here)
    return "PLATINUM"


def update_after_session(ctx: DoctrineContext, result_u: float, new_GA: float, old_state: str):
    """
    Update context after a session completes.
    Tracks session results, peak GA, and state-specific counters.
    
    Args:
        ctx: Doctrine context to update
        result_u: Session result in units (can be negative)
        new_GA: New bankroll after session
        old_state: The state that was used for this session
    """
    ctx.last_result_u = result_u
    ctx.GA_current = new_GA
    ctx.GA_peak = max(ctx.GA_peak, ctx.GA_current)
    ctx.total_sessions += 1
    
    # Increment state-specific counters
    if old_state == "TIGHT":
        ctx.tight_sessions_done += 1
        ctx.tight_sessions += 1
    elif old_state == "PLATINUM":
        ctx.platinum_sessions += 1
    
    # Reset TIGHT counter if we're not in TIGHT anymore
    if ctx.state != "TIGHT":
        ctx.tight_sessions_done = 0


def update_after_month(ctx: DoctrineContext):
    """
    Update context after a full month (used for cool-off tracking).
    
    Args:
        ctx: Doctrine context to update
    """
    if ctx.state == "COOL_OFF":
        ctx.cooloff_months_done += 1
        ctx.cooloff_months += 1


def roulette_stake_multiplier(ctx: DoctrineContext, rules: DoctrineStateRules) -> float:
    """
    Calculate roulette stake multiplier based on current doctrine state.
    Allows roulette betting to scale with doctrine severity.
    
    Args:
        ctx: Current doctrine context
        rules: State rules including roulette coupling config
        
    Returns:
        Multiplier to apply to roulette base stakes (0.0 - 1.0+)
    """
    if not rules.link_roulette_to_state:
        return 1.0
    
    if ctx.state == "PLATINUM":
        return rules.roulette_scale_platinum
    if ctx.state == "TIGHT":
        return rules.roulette_scale_tight
    return rules.roulette_scale_cooloff


def get_doctrine_config(state: str, platinum_cfg: DoctrineConfig, tight_cfg: DoctrineConfig) -> DoctrineConfig:
    """
    Get the appropriate doctrine configuration for the current state.
    
    Args:
        state: Current state ("PLATINUM", "TIGHT", or "COOL_OFF")
        platinum_cfg: Configuration for Platinum doctrine
        tight_cfg: Configuration for Tight doctrine
        
    Returns:
        Active doctrine configuration
    """
    if state == "TIGHT":
        return tight_cfg
    elif state == "COOL_OFF":
        # Cool-off uses ultra-conservative settings (can be customized)
        return DoctrineConfig(
            stop_loss_u=5.0,
            target_u=5.0,
            press_wins=999,  # Never press in cool-off
            press_depth=0,
            iron_gate=2
        )
    else:  # PLATINUM or default
        return platinum_cfg


def log_state_transition(ctx: DoctrineContext, old_state: str, new_state: str, reason: str):
    """
    Record a state transition for logging and analysis.
    
    Args:
        ctx: Doctrine context
        old_state: Previous state
        new_state: New state
        reason: Reason for transition
    """
    transition = {
        'session': ctx.total_sessions,
        'from': old_state,
        'to': new_state,
        'reason': reason,
        'GA': ctx.GA_current,
        'peak': ctx.GA_peak,
        'drawdown': ctx.GA_peak - ctx.GA_current,
        'drawdown_pct': (ctx.GA_peak - ctx.GA_current) / ctx.GA_peak if ctx.GA_peak > 0 else 0
    }
    ctx.transitions.append(transition)


# ============================================================================
# DEFAULT CONFIGURATIONS
# ============================================================================

# Default Platinum Doctrine (standard evening gameplay)
DEFAULT_PLATINUM = DoctrineConfig(
    stop_loss_u=10.0,
    target_u=10.0,
    press_wins=3,
    press_depth=3,
    iron_gate=3
)

# Default Tight Doctrine (conservative recovery mode)
DEFAULT_TIGHT = DoctrineConfig(
    stop_loss_u=5.0,
    target_u=5.0,
    press_wins=5,
    press_depth=1,
    iron_gate=2
)

# Default State Rules
DEFAULT_STATE_RULES = DoctrineStateRules(
    loss_trigger_pl_u=8.0,
    drawdown_trigger_pct=0.15,
    drawdown_trigger_eur=3000.0,
    tight_min_sessions=1,
    tight_max_sessions=2,
    cooloff_enabled=True,
    cooloff_ga_floor=3000.0,
    cooloff_min_months=1,
    cooloff_recovery_drawdown_pct=0.07,
    link_roulette_to_state=False,
    roulette_scale_platinum=1.0,
    roulette_scale_tight=0.5,
    roulette_scale_cooloff=0.0
)
