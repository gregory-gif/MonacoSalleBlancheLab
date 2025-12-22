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
    # --- CORE RISK ---
    iron_gate_limit: int = 3
    stop_loss_units: int = 10
    profit_lock_units: int = 10
    
    # --- PROGRESSION ---
    press_trigger_wins: int = 1
    press_depth: int = 3
    ratchet_enabled: bool = False
    ratchet_mode: str = 'Standard'
    ratchet_lock_pct: float = 0.5
    
    # --- BET SELECTION ---
    bet_strategy: any = BetStrategy.BANKER 
    bet_strategy_2: str = None 
    
    # --- SESSION ---
    shoes_per_session: int = 3
    penalty_box_enabled: bool = True
    
    # --- SPICE BETS CONFIGURATION v5.0 (7 Spice Types) ---
    # Global Spice Controls
    spice_global_max_per_session: int = 3
    spice_global_max_per_spin: int = 1
    spice_disable_if_caroline_step4: bool = True
    spice_disable_if_pl_below_zero: bool = True
    
    # Family A - Light Spices
    spice_zero_leger_enabled: bool = False
    spice_zero_leger_trigger: int = 15
    spice_zero_leger_max: int = 2
    spice_zero_leger_cooldown: int = 5
    spice_zero_leger_min_pl: int = 15
    spice_zero_leger_max_pl: int = 80
    
    spice_jeu_zero_enabled: bool = False
    spice_jeu_zero_trigger: int = 15
    spice_jeu_zero_max: int = 2
    spice_jeu_zero_cooldown: int = 5
    spice_jeu_zero_min_pl: int = 15
    spice_jeu_zero_max_pl: int = 80
    
    spice_zero_crown_enabled: bool = False
    spice_zero_crown_trigger: int = 15
    spice_zero_crown_max: int = 2
    spice_zero_crown_cooldown: int = 5
    spice_zero_crown_min_pl: int = 15
    spice_zero_crown_max_pl: int = 80
    
    # Family B - Medium Spices
    spice_tiers_enabled: bool = False
    spice_tiers_trigger: int = 25
    spice_tiers_max: int = 1
    spice_tiers_cooldown: int = 8
    spice_tiers_min_pl: int = 25
    spice_tiers_max_pl: int = 80
    
    spice_orphelins_enabled: bool = False
    spice_orphelins_trigger: int = 25
    spice_orphelins_max: int = 1
    spice_orphelins_cooldown: int = 8
    spice_orphelins_min_pl: int = 25
    spice_orphelins_max_pl: int = 80
    
    # Family C - Prestige Spices
    spice_orphelins_plein_enabled: bool = False
    spice_orphelins_plein_trigger: int = 35
    spice_orphelins_plein_max: int = 1
    spice_orphelins_plein_cooldown: int = 10
    spice_orphelins_plein_min_pl: int = 35
    spice_orphelins_plein_max_pl: int = 100
    
    spice_voisins_enabled: bool = False
    spice_voisins_trigger: int = 35
    spice_voisins_max: int = 1
    spice_voisins_cooldown: int = 10
    spice_voisins_min_pl: int = 35
    spice_voisins_max_pl: int = 100
    
    # --- TAX ---
    tax_threshold: float = 12500.0
    tax_rate: float = 25.0

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
    
    is_in_virtual_mode: bool = False
    virtual_loss_counter: int = 0

class BaccaratStrategist:
    @staticmethod
    def get_next_decision(state: SessionState):
        base_val = state.tier.base_unit
        
        if state.is_in_virtual_mode:
            target = state.overrides.bet_strategy.name if hasattr(state.overrides.bet_strategy, 'name') else str(state.overrides.bet_strategy)
            return {'mode': PlayMode.PLAYING, 'bet_amount': 0, 'reason': 'VIRTUAL (OBSERVING)', 'bet_target': target}

        stop_limit = state.tier.stop_loss
        if state.overrides.stop_loss_units > 0:
            stop_limit = -(state.overrides.stop_loss_units * base_val)
        
        if state.session_pnl <= stop_limit:
            return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'HARD STOP LOSS', 'bet_target': 'NONE'}

        if state.overrides.profit_lock_units > 0:
            target = state.overrides.profit_lock_units * base_val
            is_gold_grinding = (state.overrides.ratchet_mode == 'Gold Grinder' and state.current_shoe < 3)
            if state.session_pnl >= target and not is_gold_grinding:
                return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'TARGET HIT', 'bet_target': 'NONE'}

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

        if state.consecutive_losses >= state.overrides.iron_gate_limit:
            state.is_in_virtual_mode = True
            state.current_press_streak = 0
            state.consecutive_losses = 0 
            target = state.overrides.bet_strategy.name if hasattr(state.overrides.bet_strategy, 'name') else str(state.overrides.bet_strategy)
            return {'mode': PlayMode.PLAYING, 'bet_amount': 0, 'reason': 'IRON GATE TRIGGERED', 'bet_target': target}

        bet = base_val
        pm = state.overrides.press_trigger_wins
        if pm == 3: 
            if state.current_press_streak == 1: bet = base_val * 1.5
            elif state.current_press_streak >= 2: bet = base_val * 2.5
        elif pm > 0: 
            if state.current_press_streak >= pm:
                steps = min(state.current_press_streak, state.overrides.press_depth)
                bet = base_val + (steps * state.tier.press_unit)

        target = state.overrides.bet_strategy.name if hasattr(state.overrides.bet_strategy, 'name') else str(state.overrides.bet_strategy)
        return {'mode': PlayMode.PLAYING, 'bet_amount': bet, 'reason': 'ACTION', 'bet_target': target}

    @staticmethod
    def update_state_after_hand(state: SessionState, won: bool, pnl_change: float):
        if state.is_in_virtual_mode:
            if won:
                state.is_in_virtual_mode = False
                state.consecutive_losses = 0
                state.current_press_streak = 1 
            else:
                state.virtual_loss_counter += 1
            state.hands_played_total += 1
            return 

        final_pnl = pnl_change
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
