"""
Test Suite for Fibonacci Hunter Progression
============================================
Tests the complete Fibonacci Hunter betting strategy:
- Sequence: [1, 1, 2, 3, 5, 8] units
- Win: Move to next step
- Loss: Hard reset to step 1
- Max Win: Session exit (Sniper Mode)
"""

from engine.baccarat_rules import BaccaratSessionState, BaccaratStrategist
from engine.strategy_rules import StrategyOverrides, BetStrategy, PlayMode
from engine.tier_params import TierConfig


def create_fibonacci_hunter_state(base_unit=100, action_on_max_win='STOP_SESSION'):
    """Create a test state with Fibonacci Hunter enabled"""
    tier = TierConfig(
        level=1,
        min_ga=0,
        max_ga=99999,
        base_unit=10,  # Standard base (Fibonacci has its own base)
        press_unit=10,
        stop_loss=-1000,
        profit_lock=2000,
        catastrophic_cap=-5000
    )
    
    overrides = StrategyOverrides(
        fibonacci_hunter_enabled=True,
        fibonacci_hunter_base_unit=base_unit,
        fibonacci_hunter_max_step=5,  # Index 5 = 8 units
        fibonacci_hunter_action_on_max_win=action_on_max_win,
        bet_strategy=BetStrategy.BANKER,  # Fibonacci overrides to PLAYER
        stop_loss_units=50,  # High stop loss to avoid interference
        profit_lock_units=0,  # No profit target
        iron_gate_limit=999  # Disable iron gate for testing
    )
    
    return BaccaratSessionState(tier=tier, overrides=overrides)


def test_1_basic_progression():
    """Test basic win progression through sequence"""
    print("\n" + "="*70)
    print("TEST 1: Basic Win Progression")
    print("="*70)
    
    state = create_fibonacci_hunter_state(base_unit=100)
    sequence = [1, 1, 2, 3, 5, 8]
    
    for step in range(len(sequence)):
        decision = BaccaratStrategist.get_next_decision(state)
        expected_bet = 100 * sequence[step]
        
        print(f"\nStep {step + 1}/{len(sequence)}:")
        print(f"  Expected Bet: {expected_bet}")
        print(f"  Actual Bet:   {decision['bet_amount']}")
        print(f"  Reason:       {decision['reason']}")
        print(f"  Target:       {decision['bet_target']}")
        
        assert decision['bet_amount'] == expected_bet, f"Bet mismatch at step {step + 1}"
        assert decision['bet_target'] == 'PLAYER', "Should always bet PLAYER"
        
        # Simulate win (except on last step to test separately)
        if step < len(sequence) - 1:
            BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=expected_bet)
            print(f"  Result:       WIN (+{expected_bet})")
    
    print("\n✓ Basic progression sequence works correctly")


def test_2_hard_reset_on_loss():
    """Test hard reset behavior on any loss"""
    print("\n" + "="*70)
    print("TEST 2: Hard Reset on Loss")
    print("="*70)
    
    state = create_fibonacci_hunter_state(base_unit=100)
    sequence = [1, 1, 2, 3, 5, 8]
    
    # Progress to step 4 (300 units)
    for step in range(3):
        decision = BaccaratStrategist.get_next_decision(state)
        BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=decision['bet_amount'])
        print(f"Step {step + 1}: WIN at {decision['bet_amount']} units")
    
    # Now at step 4 (index 3 = 300 units)
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"\nAt Step 4: Betting {decision['bet_amount']} units")
    assert decision['bet_amount'] == 300, "Should be at 300 units (step 4)"
    
    # LOSE
    BaccaratStrategist.update_state_after_hand(state, won=False, pnl_change=-300)
    print("Result: LOSS (-300)")
    
    # Should reset to step 1 (100 units)
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"\nAfter Loss - Next Bet: {decision['bet_amount']} units")
    assert decision['bet_amount'] == 100, "Should hard reset to 100 units (step 1)"
    assert state.fibonacci_hunter_step_index == 0, "Step index should reset to 0"
    
    print("\n✓ Hard reset on loss works correctly")


def test_3_multiple_resets():
    """Test multiple loss resets at different levels"""
    print("\n" + "="*70)
    print("TEST 3: Multiple Loss Resets")
    print("="*70)
    
    state = create_fibonacci_hunter_state(base_unit=100)
    
    # Test case from requirements:
    # Bet 1 (100) -> WIN
    # Bet 2 (100) -> WIN
    # Bet 3 (200) -> WIN
    # Bet 4 (300) -> LOSE -> Reset to 100
    # Bet 1 (100) -> LOSE -> Stay at 100
    
    test_sequence = [
        (True, 100, "Step 1 WIN"),
        (True, 100, "Step 2 WIN"),
        (True, 200, "Step 3 WIN"),
        (False, 300, "Step 4 LOSS -> RESET"),
        (False, 100, "Step 1 LOSS (stay at base)"),
        (True, 100, "Step 1 WIN"),
        (True, 100, "Step 2 WIN"),
    ]
    
    for i, (should_win, expected_bet, description) in enumerate(test_sequence):
        decision = BaccaratStrategist.get_next_decision(state)
        print(f"\n{i+1}. {description}")
        print(f"   Expected: {expected_bet} | Actual: {decision['bet_amount']}")
        
        assert decision['bet_amount'] == expected_bet, f"Bet mismatch: {description}"
        
        pnl = expected_bet if should_win else -expected_bet
        BaccaratStrategist.update_state_after_hand(state, won=should_win, pnl_change=pnl)
        print(f"   Result: {'WIN' if should_win else 'LOSS'} ({'+' if should_win else ''}{pnl})")
    
    print("\n✓ Multiple resets work correctly")


def test_4_sniper_mode_exit():
    """Test session exit after winning the killer bet (8 units)"""
    print("\n" + "="*70)
    print("TEST 4: Sniper Mode - Exit on Killer Bet Win")
    print("="*70)
    
    state = create_fibonacci_hunter_state(base_unit=100, action_on_max_win='STOP_SESSION')
    sequence = [1, 1, 2, 3, 5, 8]
    
    # Win through entire sequence
    total_profit = 0
    for step in range(len(sequence)):
        decision = BaccaratStrategist.get_next_decision(state)
        bet_amount = decision['bet_amount']
        print(f"\nStep {step + 1}: Betting {bet_amount} units")
        
        # Simulate win
        BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=bet_amount)
        total_profit += bet_amount
        print(f"  WIN (+{bet_amount}) | Total Profit: {total_profit}")
        
        if step == len(sequence) - 1:
            # Just won the killer bet (800 units)
            print(f"\n🎯 KILLER BET WON! (+800 units)")
            print(f"   Total Profit from Sequence: {total_profit} units")
            assert state.mode == PlayMode.STOPPED, "Session should be stopped"
            assert state.fibonacci_hunter_max_reached == 1, "Should record max reached"
    
    # Next decision should return STOPPED
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"\nNext Decision: {decision['mode']} - {decision['reason']}")
    assert decision['mode'] == PlayMode.STOPPED, "Session should remain stopped"
    assert decision['reason'] == 'FIBONACCI TARGET HIT', "Should show target hit reason"
    
    print("\n✓ Sniper mode exit works correctly")
    print(f"✓ Total sequence profit: {total_profit} units (Expected: 2000)")


def test_5_reset_and_continue_mode():
    """Test RESET_AND_CONTINUE mode (for longer sessions)"""
    print("\n" + "="*70)
    print("TEST 5: Reset and Continue Mode")
    print("="*70)
    
    state = create_fibonacci_hunter_state(base_unit=100, action_on_max_win='RESET_AND_CONTINUE')
    sequence = [1, 1, 2, 3, 5, 8]
    
    # Win through entire sequence
    for step in range(len(sequence)):
        decision = BaccaratStrategist.get_next_decision(state)
        print(f"Step {step + 1}: Betting {decision['bet_amount']} units")
        BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=decision['bet_amount'])
    
    print(f"\n✓ Completed full sequence")
    print(f"  Cycles completed: {state.fibonacci_hunter_total_cycles}")
    print(f"  Max reached: {state.fibonacci_hunter_max_reached}")
    
    # Should reset to step 1 and continue
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"\nNext bet after completing sequence: {decision['bet_amount']} units")
    assert decision['bet_amount'] == 100, "Should reset to 100 units"
    assert state.mode == PlayMode.PLAYING, "Session should continue playing"
    assert state.fibonacci_hunter_step_index == 0, "Should reset to index 0"
    
    print("\n✓ Reset and continue mode works correctly")


def test_6_tie_handling():
    """Test that ties don't affect progression"""
    print("\n" + "="*70)
    print("TEST 6: Tie Handling")
    print("="*70)
    
    state = create_fibonacci_hunter_state(base_unit=100)
    
    # Win first hand
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"Step 1: Bet {decision['bet_amount']} -> WIN")
    BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=100)
    
    # Tie on second hand
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"Step 2: Bet {decision['bet_amount']} -> TIE (push)")
    assert decision['bet_amount'] == 100, "Should be at step 2 (100 units)"
    BaccaratStrategist.update_state_after_hand(state, won=False, pnl_change=0, was_tie=True)
    
    # Should remain at step 2
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"After Tie: Bet {decision['bet_amount']}")
    assert decision['bet_amount'] == 100, "Should stay at step 2 after tie"
    assert state.fibonacci_hunter_step_index == 1, "Step index should remain 1"
    
    print("\n✓ Ties don't affect progression correctly")


def test_7_stop_loss_integration():
    """Test stop loss overrides progression"""
    print("\n" + "="*70)
    print("TEST 7: Stop Loss Integration")
    print("="*70)
    
    state = create_fibonacci_hunter_state(base_unit=100)
    state.overrides.stop_loss_units = 5  # Very low stop loss
    
    # Lose a few bets to hit stop loss
    for i in range(6):
        decision = BaccaratStrategist.get_next_decision(state)
        if decision['mode'] == PlayMode.STOPPED:
            print(f"\n✓ Stop loss triggered after {i} losses")
            print(f"  Session P/L: {state.session_pnl}")
            print(f"  Reason: {decision['reason']}")
            break
        
        print(f"Bet {i+1}: {decision['bet_amount']} -> LOSS")
        BaccaratStrategist.update_state_after_hand(state, won=False, pnl_change=-decision['bet_amount'])
    
    assert decision['mode'] == PlayMode.STOPPED, "Should hit stop loss"
    assert decision['reason'] == 'HARD STOP LOSS', "Should show stop loss reason"
    
    print("✓ Stop loss correctly overrides Fibonacci progression")


def test_8_player_side_enforcement():
    """Test that Fibonacci Hunter always bets PLAYER"""
    print("\n" + "="*70)
    print("TEST 8: PLAYER Side Enforcement")
    print("="*70)
    
    # Try to set BANKER as strategy
    state = create_fibonacci_hunter_state(base_unit=100)
    state.overrides.bet_strategy = BetStrategy.BANKER
    
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"Config set to BANKER")
    print(f"Actual bet target: {decision['bet_target']}")
    
    assert decision['bet_target'] == 'PLAYER', "Should override to PLAYER"
    
    print("\n✓ Fibonacci Hunter correctly enforces PLAYER bets")


def test_9_statistics_tracking():
    """Test tracking of cycles and max reached"""
    print("\n" + "="*70)
    print("TEST 9: Statistics Tracking")
    print("="*70)
    
    state = create_fibonacci_hunter_state(base_unit=100, action_on_max_win='RESET_AND_CONTINUE')
    sequence = [1, 1, 2, 3, 5, 8]
    
    # Complete 2 full cycles
    for cycle in range(2):
        print(f"\nCycle {cycle + 1}:")
        for step in range(len(sequence)):
            decision = BaccaratStrategist.get_next_decision(state)
            BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=decision['bet_amount'])
        
        print(f"  Total cycles: {state.fibonacci_hunter_total_cycles}")
        print(f"  Max reached: {state.fibonacci_hunter_max_reached}")
    
    assert state.fibonacci_hunter_total_cycles == 2, "Should have 2 completed cycles"
    assert state.fibonacci_hunter_max_reached == 2, "Should have reached max 2 times"
    
    print("\n✓ Statistics tracking works correctly")


def test_10_edge_case_calculations():
    """Test edge cases and calculations"""
    print("\n" + "="*70)
    print("TEST 10: Edge Cases and Total Profit Calculation")
    print("="*70)
    
    state = create_fibonacci_hunter_state(base_unit=100)
    sequence = [1, 1, 2, 3, 5, 8]
    
    # Calculate expected total profit from full sequence
    expected_total = sum([100 * x for x in sequence])
    print(f"Expected total profit from sequence: {expected_total} units")
    
    actual_total = 0
    for step in range(len(sequence)):
        decision = BaccaratStrategist.get_next_decision(state)
        bet = decision['bet_amount']
        BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=bet)
        actual_total += bet
    
    print(f"Actual total profit: {actual_total} units")
    assert actual_total == expected_total, f"Profit calculation mismatch"
    assert actual_total == 2000, "Total should be 2000 units (20 units if base=100)"
    
    print("\n✓ Edge case calculations correct")
    print(f"✓ Fibonacci [1,1,2,3,5,8] @ 100 base = +2000 units per cycle")


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "="*70)
    print("FIBONACCI HUNTER PROGRESSION - COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    tests = [
        test_1_basic_progression,
        test_2_hard_reset_on_loss,
        test_3_multiple_resets,
        test_4_sniper_mode_exit,
        test_5_reset_and_continue_mode,
        test_6_tie_handling,
        test_7_stop_loss_integration,
        test_8_player_side_enforcement,
        test_9_statistics_tracking,
        test_10_edge_case_calculations,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n❌ TEST FAILED: {test.__name__}")
            print(f"   Error: {e}")
        except Exception as e:
            failed += 1
            print(f"\n❌ TEST ERROR: {test.__name__}")
            print(f"   Exception: {e}")
    
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(f"✓ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎯 ALL TESTS PASSED! Fibonacci Hunter is ready for deployment.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review.")
    
    print("="*70)


if __name__ == "__main__":
    run_all_tests()
