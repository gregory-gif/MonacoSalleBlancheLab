import random
from dataclasses import dataclass
from enum import Enum, auto

class RouletteBet(Enum):
    RED = auto()
    BLACK = auto()
    EVEN = auto()
    ODD = auto()
    LOW = auto()  # Manque (1-18)
    HIGH = auto() # Passe (19-36)

# Maps winning numbers to bets
WINNING_NUMBERS = {
    RouletteBet.RED: {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36},
    RouletteBet.BLACK: {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35},
    RouletteBet.EVEN: set(range(2, 37, 2)),
    RouletteBet.ODD: set(range(1, 37, 2)),
    RouletteBet.LOW: set(range(1, 19)),
    RouletteBet.HIGH: set(range(19, 37))
}

@dataclass
class RouletteSessionState:
    tier: any
    overrides: any
    current_spin: int = 1
    session_pnl: float = 0.0
    consecutive_losses: int = 0
    current_press_streak: int = 0
    locked_profit: float = -999999.0
    
    # NEW: Specific tracker for D'Alembert level (0 to 4)
    dalembert_level: int = 0 
    
    mode: str = 'PLAYING' # 'PLAYING', 'STOPPED'

class RouletteStrategist:
    @staticmethod
    def get_next_decision(state):
        base_val = state.tier.base_unit
        
        # 1. STOP LOSS / PROFIT (Standard Checks)
        stop_limit = state.tier.stop_loss
        if state.overrides.stop_loss_units > 0:
            stop_limit = -(state.overrides.stop_loss_units * base_val)
        
        if state.session_pnl <= stop_limit:
            return {'mode': 'STOPPED', 'bet': 0, 'reason': 'STOP LOSS'}

        if state.overrides.profit_lock_units > 0:
            target = state.overrides.profit_lock_units * base_val
            if state.session_pnl >= target:
                return {'mode': 'STOPPED', 'bet': 0, 'reason': 'TARGET HIT'}

        if state.overrides.ratchet_enabled:
            if state.session_pnl <= state.locked_profit and state.locked_profit > -9999:
                return {'mode': 'STOPPED', 'bet': 0, 'reason': 'RATCHET'}
            
            curr_u = state.session_pnl / base_val
            if curr_u >= 8 and state.locked_profit < (3 * base_val): state.locked_profit = 3 * base_val
            elif curr_u >= 12 and state.locked_profit < (5 * base_val): state.locked_profit = 5 * base_val
            elif curr_u >= 20 and state.locked_profit < (10 * base_val): state.locked_profit = 10 * base_val

        # 2. BET SIZING LOGIC
        bet = base_val
        press_mode = state.overrides.press_trigger_wins
        
        # --- NEW OPTION 4: CAPPED D'ALEMBERT ---
        if press_mode == 4:
            # state.dalembert_level represents steps above base.
            # Step size = 1 Base Unit
            
            # Dynamic Step Calculation
            step_size = base_val
            bet = base_val + (state.dalembert_level * step_size)
            
            # Cap at 5 Units (Base + 4 steps)
            # Example: Base €10. Steps €10. Max Bet €50.
            max_bet = base_val * 5.0
            
            # Safety Clamp
            if bet < base_val: bet = base_val
            if bet > max_bet: bet = max_bet
            
        # --- EXISTING POSITIVE PROGRESSIONS ---
        elif press_mode == 3: # Progression 1-1.5-2.5 (Titan Style)
            if state.current_press_streak == 1: bet = base_val * 1.5
            elif state.current_press_streak >= 2: bet = base_val * 2.5
            if state.consecutive_losses >= state.overrides.iron_gate_limit: state.current_press_streak = 0
            
        elif press_mode > 0: # Standard Press 1 or 2
            if state.consecutive_losses >= state.overrides.iron_gate_limit: state.current_press_streak = 0
            if state.current_press_streak >= press_mode:
                press_steps = min(state.current_press_streak, state.overrides.press_depth)
                bet = base_val + (press_steps * state.tier.press_unit)

        return {'mode': 'PLAYING', 'bet': bet, 'reason': 'ACTION'}

    @staticmethod
    def resolve_spin(state, bet_type, bet_amount):
        number = random.randint(0, 36)
        won = False
        pnl_change = 0
        
        if number == 0:
            # La Partage
            pnl_change = -(bet_amount / 2.0)
            won = False 
        else:
            winning_set = WINNING_NUMBERS[bet_type]
            if number in winning_set:
                won = True
                pnl_change = bet_amount
            else:
                won = False
                pnl_change = -bet_amount

        # Update PnL
        state.session_pnl += pnl_change
        
        # --- UPDATE STATE FOR NEXT HAND ---
        
        # D'ALEMBERT LOGIC UPDATER
        if state.overrides.press_trigger_wins == 4:
            if won:
                # Win: Decrease level
                if state.dalembert_level > 0:
                    state.dalembert_level -= 1
            else:
                # Lose: Increase level
                # CRITICAL RULE: If at Cap (Level 4) and Lose, RESET to Floor.
                if state.dalembert_level >= 4:
                    state.dalembert_level = 0 # The Reset
                else:
                    state.dalembert_level += 1
        
        # STANDARD STREAK TRACKING (For other modes)
        if won:
            state.consecutive_losses = 0
            state.current_press_streak += 1
        else:
            state.consecutive_losses += 1
            state.current_press_streak = 0 

        return number, won, pnl_change
