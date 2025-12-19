import random
from dataclasses import dataclass
from enum import Enum, auto

class RouletteBet(Enum):
    # Standard
    RED = auto()
    BLACK = auto()
    EVEN = auto()
    ODD = auto()
    LOW = auto()
    HIGH = auto()
    # Complex Strategies
    STRAT_SALON_LITE = auto()   # 26, 0/3, 32/35, Black
    STRAT_FRENCH_LITE = auto()  # Tiers, Orphelins, Black

# Winning Numbers Sets
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
    
    # Progressions
    dalembert_level: int = 0 
    caroline_level: int = 0 # 0 to 4 (1, 1, 2, 3, 4)
    
    mode: str = 'PLAYING' 

class RouletteStrategist:
    @staticmethod
    def get_next_decision(state):
        base_val = state.tier.base_unit
        
        # 1. STOP LOSS / PROFIT
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

        # 2. BET SIZING
        bet = base_val
        press_mode = state.overrides.press_trigger_wins
        
        # --- LA CAROLINE (1-1-2-3-4) ---
        if press_mode == 5:
            # Sequence: 1, 1, 2, 3, 4
            seq = [1, 1, 2, 3, 4]
            # Ensure index range
            idx = min(state.caroline_level, 4)
            multiplier = seq[idx]
            bet = base_val * multiplier

        # --- CAPPED D'ALEMBERT ---
        elif press_mode == 4:
            step_size = base_val
            bet = base_val + (state.dalembert_level * step_size)
            max_bet = base_val * 5.0
            if bet < base_val: bet = base_val
            if bet > max_bet: bet = max_bet
            
        # --- POSITIVE PROGRESSIONS ---
        elif press_mode == 3: # Titan
            if state.current_press_streak == 1: bet = base_val * 1.5
            elif state.current_press_streak >= 2: bet = base_val * 2.5
            if state.consecutive_losses >= state.overrides.iron_gate_limit: state.current_press_streak = 0
            
        elif press_mode > 0: # Standard
            if state.consecutive_losses >= state.overrides.iron_gate_limit: state.current_press_streak = 0
            if state.current_press_streak >= press_mode:
                press_steps = min(state.current_press_streak, state.overrides.press_depth)
                bet = base_val + (press_steps * state.tier.press_unit)

        return {'mode': 'PLAYING', 'bet': bet, 'reason': 'ACTION'}

    @staticmethod
    def resolve_spin(state, bet_types: list, bet_amount):
        number = random.randint(0, 36)
        net_pnl = 0.0
        
        for bt in bet_types:
            # --- COMPLEX STRATEGY 1: SALON PRIVE LITE ---
            # Ratio: 1u (26), 1u (0/3), 1u (32/35), 2u (Black). Total 5 units.
            # We treat 'bet_amount' as the 1 Unit Size.
            if bt == RouletteBet.STRAT_SALON_LITE:
                # Cost: 5 units
                cost = bet_amount * 5.0
                payout = 0.0
                
                # Check hits
                # 1. Number 26 (Straight) -> 35:1
                if number == 26: payout += (bet_amount * 35) + bet_amount
                
                # 2. Split 0/3 -> 17:1
                if number in [0, 3]: payout += (bet_amount * 17) + bet_amount
                
                # 3. Split 32/35 -> 17:1
                if number in [32, 35]: payout += (bet_amount * 17) + bet_amount
                
                # 4. Black (2 units) -> 1:1
                # Note: 0 is Green, implies loss on Black logic unless La Partage
                if number in WINNING_NUMBERS[RouletteBet.BLACK]:
                    payout += (bet_amount * 2 * 2) # Return stake (2) + Win (2)
                elif number == 0:
                    payout += (bet_amount * 2 / 2) # La Partage on the Black portion
                
                net_pnl += (payout - cost)

            # --- COMPLEX STRATEGY 2: FRENCH MAIN GAME LITE ---
            # Ratio: Tiers(3u), Orphelins(2u), Black(2u). Total 7 units.
            # Tiers (6 splits, 0.5u each -> 3u total)
            # Orphelins (1 straight + 4 splits -> we simplify to 2u total coverage)
            elif bt == RouletteBet.STRAT_FRENCH_LITE:
                cost = bet_amount * 7.0
                payout = 0.0
                
                # 1. Tiers (5,8,10,11,13,16,23,24,27,30,33,36)
                # 6 splits covering 12 numbers. Total stake 3u. Each split is 0.5u.
                # Win on split pays 17:1. 
                # Win = 0.5u * 17 = 8.5u + 0.5u stake returned = 9u payout.
                tiers_nums = {5,8,10,11,13,16,23,24,27,30,33,36}
                if number in tiers_nums:
                    payout += (bet_amount * 9.0)
                
                # 2. Orphelins (1,6,9,14,17,20,31,34)
                # Stake 2u. 5 chips. Each chip 0.4u.
                # 1 is Straight (35:1). Others Splits (17:1).
                # 17 (Split 14/17 and 17/20) is special case in full Orph but here simplified splits.
                # Simplified Payout Model for Orph (approx):
                # Any Orph hit pays roughly 18u relative to 2u stake? 
                # Let's map strict "Lite": 1 chip on 1, 6/9, 14/17, 17/20, 31/34.
                # Total 5 chips = 2u stake -> 1 chip = 0.4u.
                orph_nums = {1,6,9,14,17,20,31,34}
                if number in orph_nums:
                    if number == 1: # Straight
                        # 0.4u * 35 = 14u + 0.4u = 14.4u
                        payout += (bet_amount * 0.4 * 36)
                    elif number == 17: # Often shared in full layout, simplified here as 1 hit
                        payout += (bet_amount * 0.4 * 18)
                    else: # Split
                        payout += (bet_amount * 0.4 * 18)

                # 3. Black (2 units)
                if number in WINNING_NUMBERS[RouletteBet.BLACK]:
                    payout += (bet_amount * 4.0) # Stake 2 + Win 2
                elif number == 0:
                    payout += (bet_amount * 1.0) # La Partage on 2u
                
                net_pnl += (payout - cost)

            # --- STANDARD BETS ---
            else:
                pnl_change = 0
                if number == 0:
                    pnl_change = -(bet_amount / 2.0) # La Partage
                else:
                    winning_set = WINNING_NUMBERS[bt]
                    if number in winning_set:
                        pnl_change = bet_amount
                    else:
                        pnl_change = -bet_amount
                net_pnl += pnl_change

        state.session_pnl += net_pnl
        
        # --- PROGRESSION UPDATES ---
        won = (net_pnl > 0)
        lost = (net_pnl < 0)
        
        # LA CAROLINE (1-1-2-3-4)
        if state.overrides.press_trigger_wins == 5:
            if won:
                state.caroline_level += 1
                if state.caroline_level > 4: state.caroline_level = 4 # Cap or Cycle? Usually cap/reset. Let's Cap.
            elif lost:
                state.caroline_level = 0 # Reset on loss
        
        # D'ALEMBERT
        elif state.overrides.press_trigger_wins == 4:
            if won:
                if state.dalembert_level > 0: state.dalembert_level -= 1
            elif lost:
                if state.dalembert_level >= 4: state.dalembert_level = 0
                else: state.dalembert_level += 1
        
        # STANDARD STREAK
        if won:
            state.consecutive_losses = 0
            state.current_press_streak += 1
        elif lost:
            state.consecutive_losses += 1
            state.current_press_streak = 0

        return number, won, net_pnl
