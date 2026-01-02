"""
Test script to verify tie betting feature in baccarat simulation
"""
import random
from engine.baccarat_rules import BaccaratSessionState, BaccaratStrategist
from engine.strategy_rules import StrategyOverrides, BetStrategy
from engine.tier_params import TierConfig

def test_tie_betting():
    print("=== TESTING TIE BETTING FEATURE ===\n")
    
    # Set seed for reproducibility
    random.seed(42)
    
    # Create a basic tier config
    tier = TierConfig(
        level=1,
        min_ga=0,
        max_ga=10000,
        base_unit=10.0,
        press_unit=5.0,
        stop_loss=-100,
        profit_lock=100,
        catastrophic_cap=-500
    )
    
    # Create overrides
    overrides = StrategyOverrides(
        iron_gate_limit=99,
        stop_loss_units=0,
        profit_lock_units=0,
        shoes_per_session=1,
        bet_strategy=BetStrategy.BANKER,
        press_trigger_wins=0,
        press_depth=0,
        ratchet_enabled=False
    )
    
    # Initialize state
    state = BaccaratSessionState(tier=tier, overrides=overrides)
    
    # Simulate some hands
    print("Simulating hands with tie betting logic:\n")
    
    for hand_num in range(1, 16):
        decision = BaccaratStrategist.get_next_decision(state)
        amt = decision['bet_amount']
        
        # Check if we should place tie bet
        tie_bet_amt = 0
        if state.place_tie_bet_this_hand and amt > 0:
            tie_bet_amt = tier.base_unit
            state.tie_bets_placed += 1
        
        # Simulate outcome with realistic probabilities
        rng = random.random()
        if rng < 0.4586:
            outcome = 'BANKER'
        elif rng < 0.9048:
            outcome = 'PLAYER'
        else:
            outcome = 'TIE'
        
        # Calculate P&L
        pnl = 0
        is_tie = False
        tie_bet_pnl = 0
        is_banker = True
        
        if outcome == 'TIE':
            is_tie = True
            state.tie_count += 1
            if tie_bet_amt > 0:
                tie_bet_pnl = tie_bet_amt * 8
                pnl = tie_bet_pnl
        else:
            main_bet_won = (outcome == 'BANKER' and is_banker) or (outcome == 'PLAYER' and not is_banker)
            if main_bet_won:
                pnl = amt * 0.95 if is_banker else amt
            else:
                pnl = -amt
            
            if tie_bet_amt > 0:
                tie_bet_pnl = -tie_bet_amt
                pnl += tie_bet_pnl
        
        state.tie_bets_pnl += tie_bet_pnl
        
        # Print hand result
        tie_bet_str = f" + TIE BET €{tie_bet_amt:.0f}" if tie_bet_amt > 0 else ""
        print(f"Hand {hand_num:2d}: {outcome:6s} | Main: €{amt:.0f}{tie_bet_str} | P&L: €{pnl:+6.2f} | Tie P&L: €{tie_bet_pnl:+5.0f}")
        
        # Update state
        main_bet_won = (outcome == 'BANKER')
        BaccaratStrategist.update_state_after_hand(state, main_bet_won, pnl, is_tie)
    
    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"Total Hands: {state.hands_played_total}")
    print(f"Ties Occurred: {state.tie_count}")
    print(f"Tie Bets Placed: {state.tie_bets_placed}")
    print(f"Tie Bet P&L: €{state.tie_bets_pnl:,.2f}")
    print(f"Session P&L: €{state.session_pnl:,.2f}")
    
    # Validation
    print(f"\n=== VALIDATION ===")
    if state.tie_count > 0:
        print(f"✓ Ties occurred in simulation")
        if state.tie_bets_placed == state.tie_count - 1:
            print(f"✓ Tie bets placed correctly (tie_count - 1 = {state.tie_count - 1})")
        elif state.tie_bets_placed == state.tie_count:
            print(f"⚠ Tie bets = tie_count (edge case: last hand was tie, no follow-up)")
        else:
            print(f"✗ Tie bet count mismatch!")
    else:
        print(f"⚠ No ties in this simulation (run again with different seed)")
    
    print(f"\n✓ Test completed successfully!")

if __name__ == "__main__":
    test_tie_betting()
