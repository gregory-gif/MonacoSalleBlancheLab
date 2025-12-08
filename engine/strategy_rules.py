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
    GOLD_CHURN = auto()  # New mode for SBM Gold Churn
    STOPPED = auto()

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
    
    # 4. Gold Churn
    gold_churn_enabled: bool = False
    gold_churn_threshold: int = 2    # Min units to start churn
    gold_churn_hands: int = 10       # Max hands to churn

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
    shoe_pnls: Dict[int, float] = field(default_factory=lambda: {1: 0.0, 2: 0.0, 3: 0.0})
    
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
    gold_churn_hands_played: int = 0
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
        # Load defaults or overrides
        base_unit = state.tier.base_unit
        press_unit = state.tier.press_unit
        
        if state.overrides:
            stop_limit = -(base_unit * state.overrides.stop_loss_units)
            profit_target = base_unit * state.overrides.profit_lock_units
        else:
            stop_limit = state.tier.stop_loss
            profit_target = state.tier.profit_lock

        # --- 1. GLOBAL STOP CHECKS ---
        
        # A. Stop Loss / Ratchet Floor
        # If Ratchet is active, locked_profit rises. If not, it stays at stop_loss.
        if state.session_pnl <= state.locked_profit or state.session_pnl <= stop_limit:
            return {'bet_amount': 0, 'reason': "STOP LOSS / RATCHET HIT", 'mode': PlayMode.STOPPED}
        
        # B. Shoe 3 Survival Rule
        if state.current_shoe == 3:
            s3_trigger = base_unit * (state.overrides.shoe3_survival_trigger if state.overrides else 5)
            s3_drop = base_unit * (state.overrides.shoe3_drop_limit if state.overrides else 1)
            
            # If we entered Shoe 3 with > +5u, we protect +1u
            if state.shoe3_start_pnl >= s3_trigger:
                if state.session_pnl <= s3_drop:
                     return {'bet_amount': 0, 'reason': "SHOE 3 SURVIVAL STOP", 'mode': PlayMode.STOPPED}
                # Force Flat betting in Survival Mode
                base_unit = state.tier.base_unit # Ensure no press
                press_unit = state.tier.base_unit

        # C. Profit Target & Gold Churn
        # If we hit the profit target, check if we should Churn or Stop
        if state.session_pnl >= profit_target and state.mode != PlayMode.GOLD_CHURN:
            if state.overrides and state.overrides.gold_churn_enabled:
                churn_floor = base_unit * state.overrides.gold_churn_threshold
                if state.session_pnl >= churn_floor:
                    # Switch to Churn Mode
                    state.mode = PlayMode.GOLD_CHURN
                    state.gold_churn_hands_played = 0
                    return {'bet_amount': 0, 'reason': "ENTERING GOLD CHURN", 'mode': PlayMode.GOLD_CHURN}
            
            return {'bet_amount': 0, 'reason': "PROFIT TARGET SECURED", 'mode': PlayMode.STOPPED}

        # --- 2. MODE SPECIFIC LOGIC ---
        
        # GOLD CHURN MODE
        if state.mode == PlayMode.GOLD_CHURN:
            limit_hands = state.overrides.gold_churn_hands if state.overrides else 10
            drop_limit = base_unit * (state.overrides.shoe3_drop_limit if state.overrides else 1) # Reuse drop limit
            
            if state.gold_churn_hands_played >= limit_hands:
                return {'bet_amount': 0, 'reason': "GOLD CHURN COMPLETE", 'mode': PlayMode.STOPPED}
            
            if state.session_pnl <= drop_limit:
                 return {'bet_amount': 0, 'reason': "GOLD CHURN STOP LOSS", 'mode': PlayMode.STOPPED}
            
            # Churn Bet Size: Tier 3+ = 100, else 50 (Approximation based on tier)
            bet = 100 if base_unit >= 100 else 50
            return {'bet_amount': bet, 'reason': f"Churn Hand {state.gold_churn_hands_played+1}", 'mode': PlayMode.GOLD_CHURN}

        # WATCHER (IRON GATE)
        if state.mode == PlayMode.WATCHER:
            return {'bet_amount': 0, 'reason': "IRON GATE: Watching", 'mode': PlayMode.WATCHER}

        # --- 3. ACTIVE BETTING LOGIC ---
        
        bet = base_unit
        reason = "Base Bet"

        # A. Tripwire (Shoe 1 Defense)
        if state.shoe1_tripwire_triggered:
            # Drop to flat €50 (or Tier 1 equivalent)
            return {'bet_amount': 50, 'reason': "TRIPWIRE: Flat €50", 'mode': PlayMode.ACTIVE}

        # B. Penalty / Cooldown Re-entry
        if state.penalty_cooldown > 0:
            return {'bet_amount': base_unit, 'reason': f"RE-ENTRY ({state.penalty_cooldown})", 'mode': PlayMode.ACTIVE}

        # C. Press Logic (Sniper/Streak)
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
        # 1. Financial Update
        state.session_pnl += amount_won
        state.shoe_pnls[state.current_shoe] += amount_won
        state.hands_played_in_shoe += 1
        state.hands_played_total += 1
        
        if state.mode == PlayMode.GOLD_CHURN:
            state.gold_churn_hands_played += 1
            # In Churn, we just update stats, we don't trigger press logic
            return

        # 2. Ratchet Logic (Lock Profit)
        if state.session_pnl > state.peak_session_pnl:
            state.peak_session_pnl = state.session_pnl
            
            if state.overrides and state.overrides.ratchet_enabled:
                # Lock x% of peak profit (only if positive)
                if state.peak_session_pnl > 0:
                    lock_amt = state.peak_session_pnl * state.overrides.ratchet_lock_pct
                    if lock_amt > state.locked_profit:
                        state.locked_profit = lock_amt

        # 3. Watcher / Iron Gate Reset
        if state.mode == PlayMode.WATCHER:
            if won:
                # Resume playing
                state.mode = PlayMode.ACTIVE
                state.consecutive_wins = 0 
                state.consecutive_losses = 0
                state.penalty_cooldown = state.overrides.iron_gate_cooldown if state.overrides else 3
            return 

        # 4. Streak Tracking
        if won:
            state.consecutive_wins += 1
            state.consecutive_losses = 0
            
            # Decrease Cooldown if active
            if state.penalty_cooldown > 0:
                state.penalty_cooldown -= 1
            
            # Track Press Streak (only if bet was actually > base)
            if amount_won > state.tier.base_unit:
                state.current_press_streak += 1
            
        else:
            state.consecutive_losses += 1
            state.consecutive_wins = 0
            state.current_press_streak = 0 
            
            # Iron Gate Trigger
            limit = state.overrides.iron_gate_limit if state.overrides else 3
            if state.consecutive_losses >= limit:
                state.mode = PlayMode.WATCHER
                state.sniper_state = SniperState.RESET
                return

        # 5. Shoe 1 Tripwire Trigger
        if not state.overrides and state.current_shoe == 1 and not state.shoe1_tripwire_triggered:
            # If loss > 50% of Stop Loss
            sl_threshold = state.tier.stop_loss * (state.overrides.shoe1_tripwire_pct if state.overrides else 0.5)
            if state.session_pnl < sl_threshold:
                state.shoe1_tripwire_triggered = True
