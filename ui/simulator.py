from nicegui import ui
import plotly.graph_objects as go
import random
import asyncio
import traceback
import numpy as np

# Internal Imports
from engine.strategy_rules import SessionState, BaccaratStrategist, PlayMode, StrategyOverrides
from engine.tier_params import TIER_MAP, TierConfig, generate_tier_map, get_tier_for_ga
from utils.persistence import load_profile, save_profile

# SBM LOYALTY TIERS
SBM_TIERS = {
    'Silver': 5000,
    'Gold': 22500,
    'Platinum': 175000
}

class SimulationWorker:
    """Runs the strategy logic."""
    @staticmethod
    def run_session(current_ga: float, overrides: StrategyOverrides, tier_map: dict, use_ratchet: bool = False, penalty_mode: bool = False):
        tier = get_tier_for_ga(current_ga, tier_map)
        
        # --- PENALTY BOX LOGIC (Catastrophic Cap Hit) ---
        if penalty_mode:
            # Override Tier Defaults for Penalty Mode
            # Prestige Hold (GA >= 2k) -> Flat 100
            # Safety Exile (GA < 2k) -> Flat 50
            flat_bet = 100 if current_ga >= 2000 else 50
            
            # Create a temporary 'Penalty Tier'
            tier = TierConfig(
                level=tier.level,
                min_ga=0, max_ga=9999999,
                base_unit=flat_bet,
                press_unit=flat_bet, # No press
                stop_loss=tier.stop_loss, # Keep original stop loss risk? Or reduce? 
                # usually in penalty we just want to survive. Let's keep tier stops but flat bets.
                profit_lock=tier.profit_lock,
                catastrophic_cap=tier.catastrophic_cap
            )
            
            # Force overrides to disable pressing
            session_overrides = StrategyOverrides(
                iron_gate_limit=overrides.iron_gate_limit,
                stop_loss_units=overrides.stop_loss_units,
                profit_lock_units=overrides.profit_lock_units,
                press_trigger_wins=999, # Impossible to trigger press
                press_depth=0 # Flat only
            )
        else:
            session_overrides = overrides

        # --- RATCHET SETUP ---
        trigger_profit_amount = 0
        ratchet_triggered = False
        
        if use_ratchet and not penalty_mode:
            trigger_profit_amount = overrides.profit_lock_units * tier.base_unit
            # Update overrides with Ratchet params
            # We create a new object to avoid mutating the shared one
            session_overrides = StrategyOverrides(
                iron_gate_limit=overrides.iron_gate_limit,
                stop_loss_units=overrides.stop_loss_units,
                profit_lock_units=1000, # Remove standard lock, use Ratchet
                press_trigger_wins=overrides.press_trigger_wins,
                press_depth=overrides.press_depth,
                ratchet_enabled=True,
                ratchet_lock_pct=overrides.ratchet_lock_pct
            )
        
        state = SessionState(tier=tier, overrides=session_overrides)
        state.current_shoe = 1
        volume = 0 
        
        while state.current_shoe <= 3 and state.mode != PlayMode.STOPPED:
            decision = BaccaratStrategist.get_next_decision(state)
            
            if decision['mode'] == PlayMode.STOPPED:
                break
            
            bet = decision['bet_amount']
            volume += bet
            
            # --- RATCHET CHECK ---
            if use_ratchet and not penalty_mode:
                if not ratchet_triggered and state.session_pnl >= trigger_profit_amount:
                    ratchet_triggered = True
                
                # Check if we hit the strategist's calculated floor
                if ratchet_triggered and state.session_pnl <= state.locked_profit:
                    break 

            # --- SIMULATE HAND ---
            rnd = random.random()
            won = False
            pnl_change = 0
            is_tie = False
            
            if rnd < 0.4586: 
                won = True
                pnl_change = bet * 0.95 
            elif rnd < (0.4586 + 0.4462): 
                won = False
                pnl_change = -bet
            else: 
                is_tie = True
                pnl_change = 0

            if not is_tie:
                BaccaratStrategist.update_state_after_hand(state, won, pnl_change)
            else:
                state.hands_played_in_shoe += 1

            # --- SHOE LOGIC ---
            if state.hands_played_in_shoe >= 80:
                state.current_shoe += 1
                state.hands_played_in_shoe = 0
                state.current_press_streak = 0
                if state.current_shoe == 3:
                    state.shoe3_start_pnl = state.session_pnl

        return state.session_pnl, volume

    @staticmethod
    def run_full_career(start_ga, total_months, sessions_per_year, 
                        contrib_win, contrib_loss, overrides, use_ratchet,
                        use_tax, use_holiday, safety_factor, 
                        target_points, earn_rate):
        
        tier_map = generate_tier_map(safety_factor)
        trajectory = []
        current_ga = start_ga
        sessions_played_total = 0
        last_session_won = False
        
        m_contrib = 0
        m_tax = 0
        m_play_pnl = 0
        m_holidays = 0
        m_insolvent_months = 0 
        m_total_volume = 0 
        
        gold_hit_year = -1
        current_year_points = 0
        
        # Track YTD PnL for Catastrophic Cap
        current_year_pnl = 0.0
        
        for m in range(total_months):
            # Reset Yearly Counters
            if m > 0 and m % 12 == 0:
                current_year_points = 0
                current_year_pnl = 0.0

            # A. Luxury Tax
            tax_thresh = overrides.tax_threshold
            tax_rate = overrides.tax_rate / 100.0
            
            if use_tax and current_ga > tax_thresh:
                surplus = current_ga - tax_thresh
                tax = surplus * tax_rate
                current_ga -= tax
                m_tax += tax

            # B. Contribution
            should_contribute = True
            if use_holiday and current_ga >= 10000:
                should_contribute = False
            
            if should_contribute:
                amount = contrib_win if last_session_won else contrib_loss
                current_ga += amount
                m_contrib += amount
            else:
                m_holidays += 1
            
            # C. Play Logic
            can_play = (current_ga >= 1500)
            if not can_play:
                m_insolvent_months += 1
            
            expected_sessions = int((m + 1) * (sessions_per_year / 12))
            sessions_due = expected_sessions - sessions_played_total
            
            if can_play and sessions_due > 0:
                for _ in range(sessions_due):
                    
                    # 1. Determine Tier & Cap
                    current_tier = get_tier_for_ga(current_ga, tier_map)
                    
                    # 2. Check Catastrophic Cap (Penalty Box)
                    # Cap is negative (e.g., -1400). If PnL < -1400, we are in Penalty.
                    is_penalty = False
                    if current_year_pnl <= current_tier.catastrophic_cap:
                        is_penalty = True
                        
                    # 3. Run Session
                    pnl, vol = SimulationWorker.run_session(
                        current_ga, overrides, tier_map, use_ratchet, penalty_mode=is_penalty
                    )
                    
                    current_ga += pnl
                    m_play_pnl += pnl
                    current_year_pnl += pnl
                    sessions_played_total += 1
                    m_total_volume += vol
                    last_session_won = (pnl > 0)
                    
                    # Points
                    points = vol * (earn_rate / 100)
                    current_year_points += points
            
            # Check Gold Status
            if gold_hit_year == -1 and current_year_points >= target_points:
                gold_hit_year = (m // 12) + 1
            
            trajectory.append(current_ga)
            
        return {
            'trajectory': trajectory,
            'final_ga': current_ga,
            'contrib': m_contrib,
            'tax': m_tax,
            'play_pnl': m_play_pnl,
            'holidays': m_holidays,
            'insolvent_months': m_insolvent_months,
            'total_volume': m_total_volume,
            'gold_year': gold_hit_year
        }

def show_simulator():
    # (Insert the UI layout code from your original paste here)
    # The crucial fix was in the SimulationWorker class above.
    pass
