import random
from dataclasses import dataclass
from enum import Enum, auto
from engine.spice_system import (
    SpiceEngine, SpiceType, SpiceFamily, SpiceRule, GlobalSpiceConfig,
    DEFAULT_SPICE_CONFIG, DEFAULT_GLOBAL_SPICE_CONFIG
)

class RouletteBet(Enum):
    # Standard
    RED = auto()
    BLACK = auto()
    EVEN = auto()
    ODD = auto()
    LOW = auto()
    HIGH = auto()
    # Complex Strategies
    STRAT_SALON_LITE = auto()   
    STRAT_FRENCH_LITE = auto()
    # Spice Bets (Dynamic)
    SPICE_ZERO = auto()  # Zéro léger (3u)
    SPICE_TIERS = auto() # Tiers du Cylindre (6u)

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
    session_start_bankroll: float = 0.0
    
    # Progressions
    dalembert_level: int = 0 
    caroline_level: int = 0
    
    # Spice Engine v5.0
    spice_engine: any = None  # Will hold SpiceEngine instance
    
    # Dynamic TP (can be boosted by spice momentum)
    dynamic_tp_eur: float = 0.0  # Session-local target profit in EUR
    
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

        # Check dynamic TP (can be boosted by spice momentum) OR fallback to override setting
        target_check = state.dynamic_tp_eur if state.dynamic_tp_eur > 0 else (state.overrides.profit_lock_units * base_val if state.overrides.profit_lock_units > 0 else 0)
        if target_check > 0 and state.session_pnl >= target_check:
            return {'mode': 'STOPPED', 'bet': 0, 'reason': 'TARGET HIT'}

        if state.overrides.ratchet_enabled:
            if state.session_pnl <= state.locked_profit and state.locked_profit > -9999:
                return {'mode': 'STOPPED', 'bet': 0, 'reason': 'RATCHET'}
            
            curr_u = state.session_pnl / base_val
            if curr_u >= 8 and state.locked_profit < (3 * base_val): state.locked_profit = 3 * base_val
            elif curr_u >= 12 and state.locked_profit < (5 * base_val): state.locked_profit = 5 * base_val
            elif curr_u >= 20 and state.locked_profit < (10 * base_val): state.locked_profit = 10 * base_val

        # 2. BET SIZING (Main Strategy)
        bet = base_val
        press_mode = state.overrides.press_trigger_wins
        
        # --- LA CAROLINE (1-1-2-3-4) ---
        if press_mode == 5:
            seq = [1, 1, 2, 3, 4]
            idx = min(state.caroline_level, 4)
            bet = base_val * seq[idx]

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
    def resolve_spin(state, bet_types: list, main_bet_amount: float):
        number = random.randint(0, 36)
        net_pnl = 0.0
        
        # Base unit for Spice Bets (Fixed size, usually)
        base_unit = state.tier.base_unit
        
        for bt in bet_types:
            
            # --- SPICE: ZERO LEGER (3u) ---
            if bt == RouletteBet.SPICE_ZERO:
                # Cost: 3 units (1 on 26, 1 on 0/3, 1 on 32/35)
                # Payouts based on 1 unit stake per chip
                cost = base_unit * 3.0
                payout = 0.0
                
                if number == 26: payout = (base_unit * 35) + base_unit
                elif number in [0, 3]: payout = (base_unit * 17) + base_unit
                elif number in [32, 35]: payout = (base_unit * 17) + base_unit
                
                net_pnl += (payout - cost)

            # --- SPICE: TIERS DU CYLINDRE (6u) ---
            elif bt == RouletteBet.SPICE_TIERS:
                # Cost: 6 units (6 splits)
                cost = base_unit * 6.0
                payout = 0.0
                
                tiers_nums = {5,8,10,11,13,16,23,24,27,30,33,36}
                if number in tiers_nums:
                    # All are splits (17:1)
                    payout = (base_unit * 17) + base_unit
                
                net_pnl += (payout - cost)

            # --- COMPLEX STRATEGY 1: SALON PRIVE LITE (Main Bet) ---
            # Uses 'main_bet_amount' which might be scaled by progression
            elif bt == RouletteBet.STRAT_SALON_LITE:
                bet_u = main_bet_amount # This acts as the "1 unit" for this pattern
                cost = bet_u * 5.0
                payout = 0.0
                
                if number == 26: payout += (bet_u * 35) + bet_u
                if number in [0, 3]: payout += (bet_u * 17) + bet_u
                if number in [32, 35]: payout += (bet_u * 17) + bet_u
                
                if number in WINNING_NUMBERS[RouletteBet.BLACK]:
                    payout += (bet_u * 2 * 2) 
                elif number == 0:
                    payout += (bet_u * 2 / 2) 
                
                net_pnl += (payout - cost)

            # --- COMPLEX STRATEGY 2: FRENCH MAIN GAME LITE (Main Bet) ---
            elif bt == RouletteBet.STRAT_FRENCH_LITE:
                bet_u = main_bet_amount
                cost = bet_u * 7.0
                payout = 0.0
                
                tiers_nums = {5,8,10,11,13,16,23,24,27,30,33,36}
                if number in tiers_nums:
                    payout += (bet_u * 9.0) # (0.5u * 17) + 0.5u
                
                orph_nums = {1,6,9,14,17,20,31,34}
                if number in orph_nums:
                    # Simplified average payout for Orph Lite (approx 14.4u on hit for 2u stake cost)
                    payout += (bet_u * 14.4) 

                if number in WINNING_NUMBERS[RouletteBet.BLACK]:
                    payout += (bet_u * 4.0) 
                elif number == 0:
                    payout += (bet_u * 1.0) 
                
                net_pnl += (payout - cost)

            # --- STANDARD BETS (Red, Black, etc) ---
            else:
                pnl_change = 0
                if number == 0:
                    pnl_change = -(main_bet_amount / 2.0) 
                else:
                    winning_set = WINNING_NUMBERS[bt]
                    if number in winning_set:
                        pnl_change = main_bet_amount
                    else:
                        pnl_change = -main_bet_amount
                net_pnl += pnl_change

        state.session_pnl += net_pnl
        
        # --- PROGRESSION UPDATES (Main Bet Only) ---
        # Note: We determine Win/Loss based on the NET result of the spin.
        # This means a Spice Bet win might "save" a Main Bet loss, preventing progression.
        won = (net_pnl > 0)
        lost = (net_pnl < 0)
        
        if state.overrides.press_trigger_wins == 5: # Caroline
            if won:
                state.caroline_level += 1
                if state.caroline_level > 4: state.caroline_level = 4
            elif lost:
                state.caroline_level = 0
        
        elif state.overrides.press_trigger_wins == 4: # D'Alembert
            if won:
                if state.dalembert_level > 0: state.dalembert_level -= 1
            elif lost:
                if state.dalembert_level >= 4: state.dalembert_level = 0
                else: state.dalembert_level += 1
        
        if won:
            state.consecutive_losses = 0
            state.current_press_streak += 1
        elif lost:
            state.consecutive_losses += 1
            state.current_press_streak = 0

        return number, won, net_pnl


# ============================================================================
# SPICE ENGINE v5.0 INTEGRATION
# ============================================================================

def create_spice_engine_from_overrides(overrides, unit_size: float = 10.0):
    """
    Convert StrategyOverrides spice configuration into a SpiceEngine.
    
    Args:
        overrides: StrategyOverrides containing spice config
        unit_size: Base unit size in euros
        
    Returns:
        SpiceEngine instance configured from overrides
    """
    # Build custom spice config from overrides
    spice_config = {
        SpiceType.ZERO_LEGER: SpiceRule(
            enabled=overrides.spice_zero_leger_enabled,
            family=SpiceFamily.A_LIGHT,
            trigger_pl_units=overrides.spice_zero_leger_trigger,
            max_uses_per_session=overrides.spice_zero_leger_max,
            cooldown_spins=overrides.spice_zero_leger_cooldown,
            min_pl_units=overrides.spice_zero_leger_min_pl,
            max_pl_units=overrides.spice_zero_leger_max_pl,
            unit_bet_size_eur=unit_size,
            pattern_id="ZERO_LEGER_PATTERN",
        ),
        SpiceType.JEU_ZERO: SpiceRule(
            enabled=overrides.spice_jeu_zero_enabled,
            family=SpiceFamily.A_LIGHT,
            trigger_pl_units=overrides.spice_jeu_zero_trigger,
            max_uses_per_session=overrides.spice_jeu_zero_max,
            cooldown_spins=overrides.spice_jeu_zero_cooldown,
            min_pl_units=overrides.spice_jeu_zero_min_pl,
            max_pl_units=overrides.spice_jeu_zero_max_pl,
            unit_bet_size_eur=unit_size,
            pattern_id="JEU_ZERO_PATTERN",
        ),
        SpiceType.ZERO_CROWN: SpiceRule(
            enabled=overrides.spice_zero_crown_enabled,
            family=SpiceFamily.A_LIGHT,
            trigger_pl_units=overrides.spice_zero_crown_trigger,
            max_uses_per_session=overrides.spice_zero_crown_max,
            cooldown_spins=overrides.spice_zero_crown_cooldown,
            min_pl_units=overrides.spice_zero_crown_min_pl,
            max_pl_units=overrides.spice_zero_crown_max_pl,
            unit_bet_size_eur=unit_size,
            pattern_id="ZERO_CROWN_PATTERN",
        ),
        SpiceType.TIERS: SpiceRule(
            enabled=overrides.spice_tiers_enabled,
            family=SpiceFamily.B_MEDIUM,
            trigger_pl_units=overrides.spice_tiers_trigger,
            max_uses_per_session=overrides.spice_tiers_max,
            cooldown_spins=overrides.spice_tiers_cooldown,
            min_pl_units=overrides.spice_tiers_min_pl,
            max_pl_units=overrides.spice_tiers_max_pl,
            unit_bet_size_eur=unit_size,
            pattern_id="TIERS_PATTERN",
        ),
        SpiceType.ORPHELINS: SpiceRule(
            enabled=overrides.spice_orphelins_enabled,
            family=SpiceFamily.B_MEDIUM,
            trigger_pl_units=overrides.spice_orphelins_trigger,
            max_uses_per_session=overrides.spice_orphelins_max,
            cooldown_spins=overrides.spice_orphelins_cooldown,
            min_pl_units=overrides.spice_orphelins_min_pl,
            max_pl_units=overrides.spice_orphelins_max_pl,
            unit_bet_size_eur=unit_size,
            pattern_id="ORPHELINS_PATTERN",
        ),
        SpiceType.ORPHELINS_PLEIN: SpiceRule(
            enabled=overrides.spice_orphelins_plein_enabled,
            family=SpiceFamily.C_PRESTIGE,
            trigger_pl_units=overrides.spice_orphelins_plein_trigger,
            max_uses_per_session=overrides.spice_orphelins_plein_max,
            cooldown_spins=overrides.spice_orphelins_plein_cooldown,
            min_pl_units=overrides.spice_orphelins_plein_min_pl,
            max_pl_units=overrides.spice_orphelins_plein_max_pl,
            unit_bet_size_eur=unit_size,
            pattern_id="ORPHELINS_PLEIN_PATTERN",
        ),
        SpiceType.VOISINS: SpiceRule(
            enabled=overrides.spice_voisins_enabled,
            family=SpiceFamily.C_PRESTIGE,
            trigger_pl_units=overrides.spice_voisins_trigger,
            max_uses_per_session=overrides.spice_voisins_max,
            cooldown_spins=overrides.spice_voisins_cooldown,
            min_pl_units=overrides.spice_voisins_min_pl,
            max_pl_units=overrides.spice_voisins_max_pl,
            unit_bet_size_eur=unit_size,
            pattern_id="VOISINS_PATTERN",
        ),
    }
    
    # Build global config from overrides
    global_config = GlobalSpiceConfig(
        max_total_spices_per_session=overrides.spice_global_max_per_session,
        max_spices_per_spin=overrides.spice_global_max_per_spin,
        disable_if_caroline_step4=overrides.spice_disable_if_caroline_step4,
        disable_if_pl_below_zero=overrides.spice_disable_if_pl_below_zero,
    )
    
    return SpiceEngine(spice_config, global_config)
