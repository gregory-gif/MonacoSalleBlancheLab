from dataclasses import dataclass
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
    profit_lock_units: int = 10
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
    
    # --- NEW: VIRTUAL MODE TRACKING ---
    is_in_virtual_mode: bool = False
    virtual_loss_counter: int = 0

class BaccaratStrategist:
    @staticmethod
    def get_next_decision(state: SessionState):
        base_val = state.tier.base_unit
        
        # 0. VIRTUAL MODE CHECK
        if state.is_in_virtual_mode:
            return {
                'mode': PlayMode.PLAYING, 
                'bet_amount': 0, 
                'reason': 'VIRTUAL (OBSERVING)',
                'bet_target': state.overrides.bet_strategy.name
            }

        # 1. STOP LOSS
        stop_limit = state.tier.stop_loss
        if state.overrides.stop_loss_units > 0:
            stop_limit = -(state.overrides.stop_loss_units * base_val)
        
        if state.session_pnl <= stop_limit:
            return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'HARD STOP LOSS', 'bet_target': 'NONE'}

        # 2. TAKE PROFIT
        if state.overrides.profit_lock_units > 0:
            target = state.overrides.profit_lock_units * base_val
            is_gold_grinding = (state.overrides.ratchet_mode == 'Gold Grinder' and state.current_shoe < 3)
            if state.session_pnl >= target and not is_gold_grinding:
                return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'TARGET HIT', 'bet_target': 'NONE'}

        # 3. RATCHET
        if state.overrides.ratchet_enabled:
            if state.session_pnl <= state.locked_profit and state.locked_profit > -9999:
                if state.overrides.ratchet_mode == 'Gold Grinder' and state.current_shoe < 3:
                    state.locked_profit = -999999.0
                else:
                    return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'RATCHET LOCK', 'bet_target': 'NONE'}

            # Move Lock Up
            u = state.session_pnl / base_val
            if u >= 8 and state.locked_profit < (3*base_val): state.locked_profit = 3*base_val
            elif u >= 12 and state.locked_profit < (5*base_val): state.locked_profit = 5*base_val
            elif u >= 20 and state.locked_profit < (10*base_val): state.locked_profit = 10*base_val

        # 4. IRON GATE TRIGGER
        if state.consecutive_losses >= state.overrides.iron_gate_limit:
            state.is_in_virtual_mode = True
            state.current_press_streak = 0
            state.consecutive_losses = 0 
            return {'mode': PlayMode.PLAYING, 'bet_amount': 0, 'reason': 'IRON GATE TRIGGERED', 'bet_target': state.overrides.bet_strategy.name}

        # 5. BET SIZING
        bet = base_val
        pm = state.overrides.press_trigger_wins
        if pm == 3: # Stepped
            if state.current_press_streak == 1: bet = base_val * 1.5
            elif state.current_press_streak >= 2: bet = base_val * 2.5
        elif pm > 0: # Linear
            if state.current_press_streak >= pm:
                steps = min(state.current_press_streak, state.overrides.press_depth)
                bet = base_val + (steps * state.tier.press_unit)

        return {'mode': PlayMode.PLAYING, 'bet_amount': bet, 'reason': 'ACTION', 'bet_target': state.overrides.bet_strategy.name}

    @staticmethod
    def update_state_after_hand(state: SessionState, won: bool, pnl_change: float):
        # VIRTUAL HANDLER
        if state.is_in_virtual_mode:
            if won:
                state.is_in_virtual_mode = False
                state.consecutive_losses = 0
                state.current_press_streak = 1 
            else:
                state.virtual_loss_counter += 1
            state.hands_played_total += 1
            return 

        # REAL HANDLER
        final_pnl = pnl_change
        # Commission Fix
        if won and state.overrides.bet_strategy == BetStrategy.BANKER and pnl_change > 0:
            final_pnl = pnl_change * 0.95

        state.session_pnl += final_pnl
        state.hands_played_total += 1
        
        if won:
            state.consecutive_losses = 0
            state.current_press_streak += 1
        else:
            state.consecutive_losses += 1
            state.current_press_streak = 0
