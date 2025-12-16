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
    shoe3_start_pnl: float = 0.0 # Snapshot of PnL at start of Shoe 3

class BaccaratStrategist:
    @staticmethod
    def get_next_decision(state: SessionState):
        # 1. RATCHET & STOP LOSS CHECKS
        # --------------------------------
        
        # Hard Stop Loss (Global)
        stop_limit = state.tier.stop_loss
        if state.overrides.stop_loss_units > 0:
            # Custom slider stop loss (e.g. 30 units * €100 = -€3000)
            stop_limit = -(state.overrides.stop_loss_units * state.tier.base_unit)
            
        if state.session_pnl <= stop_limit:
            return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'Stop Loss'}

        # Ratchet Logic
        if state.overrides.ratchet_enabled:
            # Calculate dynamic lock levels based on current high water mark? 
            # Simplified: Use the "Ladder" logic typically found in simulations
            
            # GOLD GRINDER EXCEPTION:
            # If in Shoe 1 or 2, and we hit the lock, we DO NOT QUIT. We reset.
            if state.overrides.ratchet_mode == 'Gold Grinder' and state.current_shoe < 3:
                if state.session_pnl <= state.locked_profit and state.locked_profit > -9999:
                    # We hit the lock, but we keep playing for volume.
                    # Reset the lock so we don't trigger this every hand
                    state.locked_profit = -999999.0
                    # We accept the drawdown and fight on.
            else:
                # Standard Behavior: Quit if below lock
                if state.session_pnl <= state.locked_profit and state.locked_profit > -9999:
                    return {'mode': PlayMode.STOPPED, 'bet_amount': 0, 'reason': 'Profit Lock'}

            # Update Lock Levels (Standard Ladder)
            current_u = state.session_pnl / state.tier.base_unit
            new_lock = state.locked_profit
            
            # Simple Ladder: +8u -> Lock +3u | +12u -> Lock +5u | +20u -> Lock +10u
            if current_u >= 8 and state.locked_profit < (3 * state.tier.base_unit):
                new_lock = 3 * state.tier.base_unit
            elif current_u >= 12 and state.locked_profit < (5 * state.tier.base_unit):
                new_lock = 5 * state.tier.base_unit
            elif current_u >= 20 and state.locked_profit < (10 * state.tier.base_unit):
                new_lock = 10 * state.tier.base_unit
                
            state.locked_profit = new_lock

        # 2. IRON GATE (Defense)
        # --------------------------------
        if state.consecutive_losses >= state.overrides.iron_gate_limit:
            # Virtual Bet Mode would go here. For sim speed, we usually just bet min or stop pressing.
            # Here we reset press streak to be safe.
            state.current_press_streak = 0

        # 3. BET SIZING (The Core Logic)
        # --------------------------------
        base = state.tier.base_unit
        bet = base

        # PRESS LOGIC SELECTOR
        # 0: Flat
        # 1: Press after 1 Win
        # 2: Press after 2 Wins
        # 3: STEPPED (100 -> 150 -> 250 Plateau)
        
        press_mode = state.overrides.press_trigger_wins
        
        if press_mode == 3: 
            # --- NEW STEPPED SYSTEM ---
            if state.current_press_streak == 0:
                bet = base # €100
            elif state.current_press_streak == 1:
                bet = base * 1.5 # €150
            else:
                # Streak 2+ (Plateau)
                bet = base * 2.5 # €250
        
        elif press_mode > 0:
            # Standard Linear Pressing
            if state.current_press_streak >= press_mode:
                # How deep into the press are we?
                press_steps = state.current_press_streak
                # Cap at press_depth
                if press_steps > state.overrides.press_depth:
                    press_steps = state.overrides.press_depth
                
                # Formula: Base + (Steps * Press_Unit)
                # Note: Press unit is usually defined in Tier, but we simplified to base for this sim logic
                # Let's assume Press Unit = Base Unit for aggressive, or 0.5 Base for mild.
                # To match previous logic:
                extra = press_steps * state.tier.press_unit 
                bet = base + extra

        return {'mode': PlayMode.PLAYING, 'bet_amount': bet, 'reason': 'Action'}

    @staticmethod
    def update_state_after_hand(state: SessionState, won: bool, pnl_change: float):
        state.session_pnl += pnl_change
        state.hands_played_total += 1
        
        if won:
            state.consecutive_losses = 0
            state.current_press_streak += 1
        else:
            state.consecutive_losses += 1
