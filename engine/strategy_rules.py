from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict
from .tier_params import TierConfig

# --- DEFINITIONS START HERE ---

class SniperState(Enum):
    WAIT = auto()
    TRIGGER = auto()
    FIRE = auto()
    RESET = auto()

class PlayMode(Enum):
    ACTIVE = auto()
    WATCHER = auto()
    PENALTY = auto()
    STOPPED = auto()

class BetStrategy(Enum):
    BANKER = auto()
    PLAYER = auto()

@dataclass
class StrategyOverrides:
    """
    Control Center: Allows the Simulator/User to inject custom variables 
    instead of hardcoded rules.
    """
    # 1. Progression & Limits
    stop_loss_units: int = 10
    profit_lock_units: int = 6
    press_trigger_wins: int = 2 
    press_depth: int = 3        # 0=Unlimited, 1-5=Max Steps
    
    # 2. Iron Gate & Defense
    iron_gate_limit: int = 3    # Consecutive losses to trigger Watcher
    iron_gate_cooldown: int = 3 # Hands to play flat/wait after resuming
    shoe1_tripwire_pct: float = 0.50 # % of Stop Loss to trigger Tier Drop in Shoe 1
    
    # 3. Ratchet & Survival
    ratchet_enabled: bool = False
    ratchet_lock_pct: float = 0.50   # Lock 50% of peak profit
    shoe3_survival_trigger: int = 5  # Units needed to trigger Shoe 3 defense
    shoe3_drop_limit: int = 1        # Units allowed to drop to in Shoe 3
    
    # 4. Financials
    tax_threshold: float = 12500.0
    tax_rate: float = 25.0

    # 5. New Variable Logic (Sandbox Mode)
    bet_strategy: BetStrategy = BetStrategy.BANKER
    shoes_per_session: int = 3
    penalty_box_enabled: bool = True

@dataclass
class SessionState:
    tier: TierConfig
    overrides: Optional[StrategyOverrides] = None
    
    # Session Progress
    current_shoe: int = 1
    hands_played_in_shoe: int = 0
    hands_played_total: int = 0
    
    # Financials
    session_pnl: float = 0.0
    locked_profit: float = -99999.0 # Ratchet floor
    peak_session_pnl: float = 0.0   # Track high water mark
    shoe_pnls: Dict[int, float] = field(default_factory=lambda: {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0})
    
    # Streaks
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    current_press_streak: int = 0 
    
    # Logic States
    sniper_state: SniperState = SniperState.WAIT
    mode: PlayMode = PlayMode.ACTIVE
    penalty_cooldown: int = 0
    
    # Flags
    shoe1_tripwire_triggered: bool = False
    shoe3_start_pnl: float = 0.0
    
    def __post_init__(self):
        # Initialize locked profit to stop loss initially
        if self.overrides:
             self.locked_profit = -(self.tier.base_unit * self.overrides.stop_loss_units)
        else:
             self.locked_profit = self.tier.stop_loss

class BaccaratStrategist:
    @staticmethod
    def get_next_decision(state: SessionState) -> dict:
        """
        The Brain: Determines Bet Amount, Mode, and Reason.
        """
        if state.mode == PlayMode.STOPPED:
             return {'bet_amount': 0, 'reason': "SESSION STOPPED", 'mode': PlayMode.STOPPED}

        # --- 0. CONFIG LOADING ---
        base_unit = state.tier.base_unit
        press_unit = state.tier.press_unit
        
        if state.overrides:
            stop_limit = -(base_unit * state.overrides.stop_loss_units)
            profit_target = base_unit * state.overrides.profit_lock_units
            shoes_max = state.overrides.shoes_per_session
        else:
            stop_limit = state.tier.stop_loss
            profit_target = state.tier.profit_lock
            shoes_max = 3

        # --- 1. GLOBAL STOP CHECKS ---
        
        # A. Stop Loss / Ratchet Floor
        if state.session_pnl <= state.locked_profit or state.session_pnl <= stop_limit:
            return {'bet_amount': 0, 'reason': "STOP LOSS / RATCHET HIT", 'mode': PlayMode.STOPPED}
        
        # B. THE COLOR UP RULE (Hardcap at 20 units)
        # If we hit +20 units, we leave immediately.
        if state.session_pnl >= (base_unit * 20):
             return {'bet_amount': 0, 'reason': "COLOR UP! (+20 Units)", 'mode': PlayMode.STOPPED}

        # C. Last Shoe Survival Rule
        if state.current_shoe == shoes_max:
            s3_trigger = base_unit * (state.overrides.shoe3_survival_trigger if state.overrides else 5)
            s3_drop = base_unit * (state.overrides.shoe3_drop_limit if state.overrides else 1)
            
            if state.shoe3_start_pnl >= s3_trigger:
                if state.session_pnl <= s3_drop:
                     return {'bet_amount': 0, 'reason': "FINAL SHOE SURVIVAL STOP", 'mode': PlayMode.STOPPED}
                base_unit = state.tier.base_unit 
                press_unit = state.tier.base_unit

        # D. Standard Profit Target (Disabled if Ratchet is ON)
        if not state.overrides.ratchet_enabled and state.session_pnl >= profit_target:
            return {'bet_amount': 0, 'reason': "PROFIT TARGET SECURED", 'mode': PlayMode.STOPPED}

        # WATCHER (IRON GATE)
        if state.mode == PlayMode.WATCHER:
            return {'bet_amount': 0, 'reason': "IRON GATE: Watching", 'mode': PlayMode.WATCHER}

        # --- 3. ACTIVE BETTING LOGIC ---
        bet = base_unit
        reason = "Base Bet"

        if state.shoe1_tripwire_triggered:
            return {'bet_amount': 50, 'reason': "TRIPWIRE: Flat €50", 'mode': PlayMode.ACTIVE}

        if state.penalty_cooldown > 0:
            return {'bet_amount': base_unit, 'reason': f"RE-ENTRY ({state.penalty_cooldown})", 'mode': PlayMode.ACTIVE}

        # Press Logic
        max_depth = state.overrides.press_depth if state.overrides else 3
        trigger_wins = state.overrides.press_trigger_wins if state.overrides else 2
        
        can_press = (state.current_press_streak < max_depth) or (max_depth == 0)
        
        if trigger_wins > 0 and state.consecutive_wins >= trigger_wins and can_press:
            bet = press_unit
            reason = f"Press Bet ({state.current_press_streak + 1}/{max_depth})"
        
        return {'bet_amount': bet, 'reason': reason, 'mode': PlayMode.ACTIVE}

    @staticmethod
    def update_state_after_hand(state: SessionState, won: bool, amount_won: float):
        """
        Updates PnL, Streaks, Ratchets, and Modes after a hand result.
        """
        state.session_pnl += amount_won
        state.shoe_pnls[state.current_shoe] += amount_won
        state.hands_played_in_shoe += 1
        state.hands_played_total += 1
        
        # --- NEW LADDER RATCHET LOGIC ---
        if state.session_pnl > state.peak_session_pnl:
            state.peak_session_pnl = state.session_pnl
            
            if state.overrides and state.overrides.ratchet_enabled:
                base = state.tier.base_unit
                current_u = state.peak_session_pnl / base
                
                # 1ST LOCK: Reach +8 > Lock +3
                if current_u >= 8 and current_u < 12:
                    lock_val = 3 * base
                    if lock_val > state.locked_profit: state.locked_profit = lock_val
                
                # 2ND LOCK: Reach +12 > Lock +5
                elif current_u >= 12 and current_u < 16:
                    lock_val = 5 * base
                    if lock_val > state.locked_profit: state.locked_profit = lock_val
                    
                # 3RD LOCK: Reach +16 > Lock +7
                elif current_u >= 16:
                    lock_val = 7 * base
                    if lock_val > state.locked_profit: state.locked_profit = lock_val

        # Watcher Reset
        if state.mode == PlayMode.WATCHER:
            if won:
                state.mode = PlayMode.ACTIVE
                state.consecutive_wins = 0 
                state.consecutive_losses = 0
                state.penalty_cooldown = state.overrides.iron_gate_cooldown if state.overrides else 3
            return 

        # Streak Tracking
        if won:
            state.consecutive_wins += 1
            state.consecutive_losses = 0
            if state.penalty_cooldown > 0:
                state.penalty_cooldown -= 1
            if amount_won > state.tier.base_unit:
                state.current_press_streak += 1
        else:
            state.consecutive_losses += 1
            state.consecutive_wins = 0
            state.current_press_streak = 0 
            
            limit = state.overrides.iron_gate_limit if state.overrides else 3
            if state.consecutive_losses >= limit:
                state.mode = PlayMode.WATCHER
                state.sniper_state = SniperState.RESET
                return

        # Tripwire
        if not state.overrides and state.current_shoe == 1 and not state.shoe1_tripwire_triggered:
            sl_threshold = state.tier.stop_loss * (state.overrides.shoe1_tripwire_pct if state.overrides else 0.5)
            if state.session_pnl < sl_threshold:
                state.shoe1_tripwire_triggered = True
