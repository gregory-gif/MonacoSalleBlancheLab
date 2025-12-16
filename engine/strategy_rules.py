from dataclasses import dataclass, field
from enum import Enum, auto

class PlayMode(Enum):
    PLAYING = auto()
    PAUSED = auto()
    STOPPED = auto()

class BetStrategy(Enum):
    BANKER = auto()
    PLAYER = auto()

@dataclass
class StrategyOverrides:
    iron_gate_limit: int = 3
    stop_loss_units: int = 10
    profit_lock_units: int = 10  # This is the "Take Profit" Target
    press_trigger_wins: int = 1
    press_depth: int = 3
    ratchet_enabled: bool = False
    ratchet_mode: str = 'Standard'
    ratchet_lock_pct: float = 0.5
    tax_threshold: float = 12500.0
    tax_rate: float = 25.0
    bet_strategy: BetStrategy = BetStrategy.BANKER
    shoes_per_session: int = 3
    penalty_box_enabled: bool = True

@dataclass
class SessionState:
    tier: any
    overrides: StrategyOverrides
    current_shoe: int = 1
    hands_played_in_shoe: int = 0
    hands_played_total: int = 0
    session_pnl: float = 0.0
    consecutive_losses: int = 0
    current_press_streak: int = 0
    locked_profit: float = -999999.0
    mode: PlayMode = PlayMode.PLAYING
    shoe3_start_pnl: float = 0.0 

class BaccaratStrategist:
    @staticmethod
    def get_next_decision(state: SessionState):
        base_val = state.tier.base_unit
        
        # ==============================================================================
        # 1. HARD STOP LOSS (THE BRAKE) - PRIORITY #1
        # ==============================================================================
        # This overrides everything. If you hit -300, you leave. No excuses.
        # We calculate the limit based on the Override Setting (Slider), not the Tier default.
        
        stop_limit = state.tier.stop_loss # Default Tier Stop
        
        if state.overrides.stop_loss_units > 0:
            # Slider Active: 10 units * 100 = -1000
            stop_limit = -(state.overrides.stop_loss_units * base_val)
            
        if state.session_pnl <= stop_limit:
            return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'HARD STOP LOSS'}

        # ==============================================================================
        # 2. HARD TAKE PROFIT (THE EXIT) - PRIORITY #2
        # ==============================================================================
        # This fixes the "Greedy Bot". Even if Ratchet is OFF, this must trigger.
        
        if state.overrides.profit_lock_units > 0:
            target_profit = state.overrides.profit_lock_units * base_val
            
            # GOLD GRINDER EXCEPTION:
            # Gold Grinder ignores profit stops in Shoe 1 & 2 to force volume.
            is_gold_grinding = (state.overrides.ratchet_mode == 'Gold Grinder' and state.current_shoe < 3)
            
            if state.session_pnl >= target_profit and not is_gold_grinding:
                return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'TARGET HIT'}

        # ==============================================================================
        # 3. RATCHET LOGIC (TRAILING STOP) - OPTIONAL
        # ==============================================================================
        if state.overrides.ratchet_enabled:
            
            # CHECK: Did we fall below the lock?
            if state.session_pnl <= state.locked_profit and state.locked_profit > -9999:
                
                # Gold Grinder Reset Logic
                if state.overrides.ratchet_mode == 'Gold Grinder' and state.current_shoe < 3:
                    state.locked_profit = -999999.0 # Reset and keep fighting
                else:
                    return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'RATCHET LOCK'}

            # UPDATE: Move the lock up?
            current_u = state.session_pnl / base_val
            
            # Simple Ladder: +8u -> Lock +3u | +12u -> Lock +5u | +20u -> Lock +10u
            if current_u >= 8 and state.locked_profit < (3 * base_val):
                state.locked_profit = 3 * base_val
            elif current_u >= 12 and state.locked_profit < (5 * base_val):
                state.locked_profit = 5 * base_val
            elif current_u >= 20 and state.locked_profit < (10 * base_val):
                state.locked_profit = 10 * base_val

        # ==============================================================================
        # 4. IRON GATE (DEFENSE)
        # ==============================================================================
        if state.consecutive_losses >= state.overrides.iron_gate_limit:
            state.current_press_streak = 0
            # Ideally pause betting here, but for sim speed we just reset momentum

        # ==============================================================================
        # 5. BET SIZING (OFFENSE)
        # ==============================================================================
        bet = base_val

        press_mode = state.overrides.press_trigger_wins
        
        if press_mode == 3: 
            # STEPPED SYSTEM (100 -> 150 -> 250)
            if state.current_press_streak == 0:
                bet = base_val # €100
            elif state.current_press_streak == 1:
                bet = base_val * 1.5 # €150
            else:
                bet = base_val * 2.5 # €250 (Plateau)
        
        elif press_mode > 0:
            # STANDARD LINEAR
            if state.current_press_streak >= press_mode:
                press_steps = min(state.current_press_streak, state.overrides.press_depth)
                # Simple Press: Base + (Steps * Base) -> Aggressive
                bet = base_val + (press_steps * state.tier.press_unit)

        return {'mode': PlayMode.PLAYING, 'bet_amount': bet, 'reason': 'ACTION'}

    @staticmethod
    def update_state_after_hand(state: SessionState, won: bool, pnl_change: float):
        state.session_pnl += pnl_change
        state.hands_played_total += 1
        
        if won:
            state.consecutive_losses = 0
            state.current_press_streak += 1
        else:
            state.consecutive_losses += 1
            state.current_press_streak = 0
