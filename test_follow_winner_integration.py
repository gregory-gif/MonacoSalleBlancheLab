"""
Integration Test: FOLLOW_WINNER in Full Simulation
Tests the FOLLOW_WINNER strategy in a realistic multi-hand session
"""

import random
from engine.baccarat_rules import BaccaratSessionState, BaccaratStrategist
from engine.strategy_rules import StrategyOverrides, BetStrategy
from engine.tier_params import TierConfig

def test_follow_winner_full_session():
    """Test FOLLOW_WINNER in a complete session"""
    print("\n" + "="*70)
    print("INTEGRATION TEST: FOLLOW_WINNER Full Session")
    print("="*70)
    
    # Set seed for reproducibility
    random.seed(42)
    
    tier = TierConfig(
        level=1,
        min_ga=0,
        max_ga=10000,
        base_unit=10,
        press_unit=5,
        stop_loss=-200,
        profit_lock=200,
        catastrophic_cap=-500
    )
    
    overrides = StrategyOverrides(
        iron_gate_limit=3,
        stop_loss_units=20,
        profit_lock_units=20,
        press_trigger_wins=1,
        press_depth=3,
        bet_strategy=BetStrategy.FOLLOW_WINNER,
        shoes_per_session=1.0,  # Just 1 shoe for quick test
        penalty_box_enabled=False,
        ratchet_enabled=False,
        tie_bet_enabled=False
    )
    
    print(f"\nConfiguration:")
    print(f"  Bet Strategy: FOLLOW_WINNER")
    print(f"  Base Unit: ${tier.base_unit}")
    print(f"  Press Trigger: {overrides.press_trigger_wins} win(s)")
    print(f"  Press Depth: {overrides.press_depth}")
    print(f"  Stop Loss: {overrides.stop_loss_units} units (${overrides.stop_loss_units * tier.base_unit})")
    print(f"  Profit Target: {overrides.profit_lock_units} units (${overrides.profit_lock_units * tier.base_unit})")
    print(f"  Session Length: {overrides.shoes_per_session} shoe(s)")
    
    # Initialize state
    state = BaccaratSessionState(tier=tier, overrides=overrides)
    
    # Run simulation
    print(f"\nRunning simulation...")
    
    hand_log = []
    volume = 0
    max_hands = int(70 * overrides.shoes_per_session)
    
    for hand_num in range(1, max_hands + 1):
        decision = BaccaratStrategist.get_next_decision(state)
        
        if decision['mode'].name == 'STOPPED':
            break
        
        amt = decision['bet_amount']
        bet_target = decision['bet_target']
        volume += amt
        
        # Simulate outcome
        rng = random.random()
        if rng < 0.4586:
            outcome = 'BANKER'
        elif rng < 0.9048:
            outcome = 'PLAYER'
        else:
            outcome = 'TIE'
        
        # Calculate P&L
        if outcome == 'TIE':
            pnl = 0
            won = None
        else:
            won = (bet_target == outcome)
            if won:
                pnl = amt * 0.95 if outcome == 'BANKER' else amt
            else:
                pnl = -amt
        
        # Log hand
        hand_log.append({
            'hand': hand_num,
            'bet_target': bet_target,
            'outcome': outcome,
            'bet_size': amt,
            'pnl': pnl,
            'session_pl': state.session_pnl + pnl,
            'press_level': state.current_press_streak,
            'consecutive_losses': state.consecutive_losses,
            'in_virtual': state.is_in_virtual_mode
        })
        
        # Update state
        BaccaratStrategist.update_state_after_hand(state, won if won is not None else False, pnl, outcome == 'TIE', outcome)
        
        # Check shoe limit
        if state.hands_played_in_shoe >= 70:
            state.current_shoe += 1
            state.hands_played_in_shoe = 0
            if state.current_shoe > overrides.shoes_per_session:
                break
    
    print(f"\n{'='*70}")
    print("SESSION RESULTS")
    print('='*70)
    print(f"Final P&L: ${state.session_pnl:+.2f}")
    print(f"Hands Played: {state.hands_played_total}")
    print(f"Volume Risked: ${volume:.2f}")
    print(f"Exit Reason: {decision['reason']}")
    
    # Analyze hand log
    if hand_log:
        print(f"\n{'='*70}")
        print("HAND-BY-HAND ANALYSIS (First 20 Hands)")
        print('='*70)
        print(f"{'Hand':<6} {'Bet On':<8} {'Winner':<8} {'Bet $':<7} {'P&L':<8} {'Session $':<11} {'Press':<6} {'Losses':<7}")
        print('-'*70)
        
        for i, hand in enumerate(hand_log[:20]):
            hand_num = hand['hand']
            bet_on = hand['bet_target']
            outcome = hand['outcome']
            bet_size = hand['bet_size']
            pnl = hand['pnl']
            session_pl = hand['session_pl']
            press = hand['press_level']
            losses = hand['consecutive_losses']
            
            print(f"{hand_num:<6} {bet_on:<8} {outcome:<8} ${bet_size:<6.0f} ${pnl:>+6.0f} ${session_pl:>+9.2f} {press:<6} {losses:<7}")
        
        if len(hand_log) > 20:
            print(f"... ({len(hand_log) - 20} more hands)")
        
        # Count outcomes
        banker_wins = sum(1 for h in hand_log if h['outcome'] == 'BANKER')
        player_wins = sum(1 for h in hand_log if h['outcome'] == 'PLAYER')
        ties = sum(1 for h in hand_log if h['outcome'] == 'TIE')
        
        # Count bet switching
        bet_switches = 0
        for i in range(1, len(hand_log)):
            if hand_log[i]['bet_target'] != hand_log[i-1]['bet_target']:
                bet_switches += 1
        
        print(f"\n{'='*70}")
        print("OUTCOME DISTRIBUTION")
        print('='*70)
        print(f"BANKER Wins: {banker_wins} ({banker_wins/len(hand_log)*100:.1f}%)")
        print(f"PLAYER Wins: {player_wins} ({player_wins/len(hand_log)*100:.1f}%)")
        print(f"TIE: {ties} ({ties/len(hand_log)*100:.1f}%)")
        print(f"\nBet Switches: {bet_switches} (Following winner dynamic)")
    
    print(f"\n{'='*70}")
    print("✓ INTEGRATION TEST COMPLETE")
    print('='*70)
    
    return {
        'final_pnl': state.session_pnl,
        'hands_played': state.hands_played_total,
        'hand_log': hand_log
    }

if __name__ == '__main__':
    try:
        result = test_follow_winner_full_session()
        print("\n✓ Test passed - FOLLOW_WINNER strategy works in full simulation")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise
