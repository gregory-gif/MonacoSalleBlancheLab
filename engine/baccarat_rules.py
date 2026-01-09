import random
from dataclasses import dataclass
from enum import Enum, auto
from engine.strategy_rules import StrategyOverrides, PlayMode, BetStrategy

@dataclass
class BaccaratSessionState:
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
    
    # Iron Gate Logic
    is_in_virtual_mode: bool = False
    virtual_loss_counter: int = 0
    
    # Tie Bet Logic
    last_hand_was_tie: bool = False
    place_tie_bet_this_hand: bool = False
    tie_count: int = 0  # Total ties occurred
    tie_bets_placed: int = 0  # Tie bets actually placed
    tie_bets_pnl: float = 0.0  # P&L from tie bets only

class BaccaratStrategist:
    @staticmethod
    def get_next_decision(state: BaccaratSessionState):
        base_val = state.tier.base_unit
        
        # 1. VIRTUAL MODE CHECK (Iron Gate)
        if state.is_in_virtual_mode:
            target = state.overrides.bet_strategy.name if hasattr(state.overrides.bet_strategy, 'name') else str(state.overrides.bet_strategy)
            return {'mode': PlayMode.PLAYING, 'bet_amount': 0, 'reason': 'VIRTUAL (OBSERVING)', 'bet_target': target}

        # 2. STOP LOSS
        stop_limit = state.tier.stop_loss
        if state.overrides.stop_loss_units > 0:
            stop_limit = -(state.overrides.stop_loss_units * base_val)
        
        if state.session_pnl <= stop_limit:
            return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'HARD STOP LOSS', 'bet_target': 'NONE'}

        # 3. PROFIT TARGET
        if state.overrides.profit_lock_units > 0:
            target = state.overrides.profit_lock_units * base_val
            is_gold_grinding = (state.overrides.ratchet_mode == 'Gold Grinder' and state.current_shoe < 3)
            if state.session_pnl >= target and not is_gold_grinding:
                return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'TARGET HIT', 'bet_target': 'NONE'}

        # 4. RATCHET LOGIC
        if state.overrides.ratchet_enabled:
            if state.session_pnl <= state.locked_profit and state.locked_profit > -9999:
                if state.overrides.ratchet_mode == 'Gold Grinder' and state.current_shoe < 3:
                    state.locked_profit = -999999.0 
                else:
                    return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'RATCHET LOCK', 'bet_target': 'NONE'}

            u = state.session_pnl / base_val
            if u >= 8 and state.locked_profit < (3*base_val): state.locked_profit = 3*base_val
            elif u >= 12 and state.locked_profit < (5*base_val): state.locked_profit = 5*base_val
            elif u >= 20 and state.locked_profit < (10*base_val): state.locked_profit = 10*base_val

        # 5. IRON GATE TRIGGER
        if state.consecutive_losses >= state.overrides.iron_gate_limit:
            state.is_in_virtual_mode = True
            state.current_press_streak = 0
            state.consecutive_losses = 0 
            target = state.overrides.bet_strategy.name if hasattr(state.overrides.bet_strategy, 'name') else str(state.overrides.bet_strategy)
            return {'mode': PlayMode.PLAYING, 'bet_amount': 0, 'reason': 'IRON GATE TRIGGERED', 'bet_target': target}

        # 6. BET SIZING (Progressions)
        bet = base_val
        pm = state.overrides.press_trigger_wins
        
        if pm == 3: # Titan
            if state.current_press_streak == 1: bet = base_val * 1.5
            elif state.current_press_streak >= 2: bet = base_val * 2.5
        elif pm > 0: 
            if state.current_press_streak >= pm:
                steps = min(state.current_press_streak, state.overrides.press_depth)
                bet = base_val + (steps * state.tier.press_unit)

        target = state.overrides.bet_strategy.name if hasattr(state.overrides.bet_strategy, 'name') else str(state.overrides.bet_strategy)
        return {'mode': PlayMode.PLAYING, 'bet_amount': bet, 'reason': 'ACTION', 'bet_target': target}

    @staticmethod
    def update_state_after_hand(state: BaccaratSessionState, won: bool, pnl_change: float, was_tie: bool = False):
        if state.is_in_virtual_mode:
            if won:
                state.is_in_virtual_mode = False
                state.consecutive_losses = 0
                state.current_press_streak = 1 
            else:
                state.virtual_loss_counter += 1
            state.hands_played_total += 1
            state.hands_played_in_shoe += 1
            state.last_hand_was_tie = was_tie
            state.place_tie_bet_this_hand = was_tie  # Set flag for next hand
            return 

        state.session_pnl += pnl_change
        state.hands_played_total += 1
        state.hands_played_in_shoe += 1
        
        # Handle tie bet flag for next hand
        state.place_tie_bet_this_hand = was_tie
        state.last_hand_was_tie = was_tie
        
        # For win/loss tracking, ties don't count
        if was_tie:
            # Tie = push on main bet, no streak impact
            pass
        elif pnl_change > 0:
            state.consecutive_losses = 0
            state.current_press_streak += 1
        else:
            state.consecutive_losses += 1
            state.current_press_streak = 0
