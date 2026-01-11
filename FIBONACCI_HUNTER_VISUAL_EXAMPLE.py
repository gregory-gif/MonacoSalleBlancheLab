"""
Fibonacci Hunter - Visual Example
==================================
Live demonstration of the Fibonacci Hunter progression strategy
showing bet sizing, progression logic, and session outcomes.
"""

from engine.baccarat_rules import BaccaratSessionState, BaccaratStrategist
from engine.strategy_rules import StrategyOverrides, BetStrategy, PlayMode
from engine.tier_params import TierConfig


def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_hand(hand_num, step, bet, result, pnl_change, total_pnl, reason=""):
    status = "✅ WIN " if result == "WIN" else "❌ LOSS" if result == "LOSS" else "🤝 TIE "
    pnl_str = f"{pnl_change:+5.0f}" if pnl_change != 0 else "   ±0"
    print(f"Hand {hand_num:2d} | Step {step}/6 | Bet: {bet:4.0f} | {status} | P&L: {pnl_str} | Total: {total_pnl:6.0f} {reason}")


def create_state(base_unit=100, action='STOP_SESSION'):
    tier = TierConfig(
        level=1, min_ga=0, max_ga=99999,
        base_unit=10, press_unit=10,
        stop_loss=-10000, profit_lock=99999, catastrophic_cap=-20000
    )
    
    overrides = StrategyOverrides(
        fibonacci_hunter_enabled=True,
        fibonacci_hunter_base_unit=base_unit,
        fibonacci_hunter_max_step=5,
        fibonacci_hunter_action_on_max_win=action,
        stop_loss_units=100,
        profit_lock_units=0,
        iron_gate_limit=999
    )
    
    return BaccaratSessionState(tier=tier, overrides=overrides)


def scenario_1_perfect_run():
    """Perfect run: Complete the sequence and hit sniper target"""
    print_header("SCENARIO 1: Perfect Sniper Run (6 Consecutive Wins)")
    
    state = create_state(base_unit=100)
    print("\nConfig: Base Unit = €100 | Mode = STOP_SESSION (Sniper)")
    print("Goal: Win all 6 steps and exit with +€2000\n")
    
    hand_num = 1
    while state.mode == PlayMode.PLAYING:
        decision = BaccaratStrategist.get_next_decision(state)
        
        if decision['mode'] == PlayMode.STOPPED:
            break
        
        bet = decision['bet_amount']
        step = state.fibonacci_hunter_step_index + 1
        
        # Simulate win
        pnl_change = bet
        BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=pnl_change)
        
        reason = ""
        if state.mode == PlayMode.STOPPED:
            reason = "🎯 KILLER BET WON - SESSION EXIT!"
        
        print_hand(hand_num, step, bet, "WIN", pnl_change, state.session_pnl, reason)
        hand_num += 1
    
    print(f"\n📊 RESULT: Session Complete")
    print(f"   Total Profit: €{state.session_pnl:.0f}")
    print(f"   Hands Played: {hand_num - 1}")
    print(f"   Cycles Completed: {state.fibonacci_hunter_total_cycles}")
    print(f"   Status: ✅ TARGET HIT - Sniper success!")


def scenario_2_reset_behavior():
    """Demonstrate hard reset on loss"""
    print_header("SCENARIO 2: Hard Reset Behavior")
    
    state = create_state(base_unit=100)
    print("\nConfig: Base Unit = €100 | Mode = STOP_SESSION")
    print("Sequence: W-W-W-L (Reset) → L (Stay) → W-W-L (Reset)\n")
    
    # Predetermined sequence
    sequence = [
        (True, "WIN - Progress to Step 2"),
        (True, "WIN - Progress to Step 3"),
        (True, "WIN - Progress to Step 4"),
        (False, "LOSS - HARD RESET to Step 1"),
        (False, "LOSS - Stay at Step 1"),
        (True, "WIN - Progress to Step 2"),
        (True, "WIN - Progress to Step 3"),
        (False, "LOSS - HARD RESET to Step 1"),
    ]
    
    hand_num = 1
    for won, description in sequence:
        decision = BaccaratStrategist.get_next_decision(state)
        bet = decision['bet_amount']
        step = state.fibonacci_hunter_step_index + 1
        
        pnl_change = bet if won else -bet
        BaccaratStrategist.update_state_after_hand(state, won=won, pnl_change=pnl_change)
        
        print_hand(hand_num, step, bet, "WIN" if won else "LOSS", pnl_change, state.session_pnl, f"← {description}")
        hand_num += 1
    
    print(f"\n📊 RESULT: Reset Demonstration Complete")
    print(f"   Total P&L: €{state.session_pnl:.0f}")
    print(f"   Hands Played: {hand_num - 1}")
    print(f"   Current Step: {state.fibonacci_hunter_step_index + 1}")


def scenario_3_marathon_mode():
    """Marathon mode: Multiple cycles"""
    print_header("SCENARIO 3: Marathon Mode (Multiple Cycles)")
    
    state = create_state(base_unit=100, action='RESET_AND_CONTINUE')
    print("\nConfig: Base Unit = €100 | Mode = RESET_AND_CONTINUE")
    print("Goal: Complete 2 full cycles (12 consecutive wins)\n")
    
    hand_num = 1
    target_cycles = 2
    
    while state.fibonacci_hunter_total_cycles < target_cycles:
        decision = BaccaratStrategist.get_next_decision(state)
        bet = decision['bet_amount']
        step = state.fibonacci_hunter_step_index + 1
        
        # Simulate win
        pnl_change = bet
        BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=pnl_change)
        
        reason = ""
        if step == 6 and state.fibonacci_hunter_step_index == 0:  # Just completed cycle
            reason = f"🔄 Cycle {state.fibonacci_hunter_total_cycles} Complete - Reset to Step 1"
        
        print_hand(hand_num, step, bet, "WIN", pnl_change, state.session_pnl, reason)
        hand_num += 1
    
    print(f"\n📊 RESULT: Marathon Session Complete")
    print(f"   Total Profit: €{state.session_pnl:.0f}")
    print(f"   Hands Played: {hand_num - 1}")
    print(f"   Cycles Completed: {state.fibonacci_hunter_total_cycles}")
    print(f"   Average per Cycle: €{state.session_pnl / state.fibonacci_hunter_total_cycles:.0f}")


def scenario_4_volatile_session():
    """Realistic volatile session with wins and losses"""
    print_header("SCENARIO 4: Volatile Session (Realistic Scenario)")
    
    state = create_state(base_unit=100)
    print("\nConfig: Base Unit = €100 | Mode = STOP_SESSION")
    print("Realistic choppy session with multiple resets\n")
    
    # More realistic sequence
    sequence = [
        (True, ""),    # Step 1 → 2
        (True, ""),    # Step 2 → 3
        (False, "Reset to 1"),  # Step 3 LOSS
        (True, ""),    # Step 1 → 2
        (False, "Reset to 1"),  # Step 2 LOSS
        (False, ""),   # Step 1 LOSS
        (True, ""),    # Step 1 → 2
        (True, ""),    # Step 2 → 3
        (True, ""),    # Step 3 → 4
        (True, ""),    # Step 4 → 5
        (False, "Reset to 1"),  # Step 5 LOSS
        (True, ""),    # Step 1 → 2
        (True, ""),    # Step 2 → 3
        (True, ""),    # Step 3 → 4
        (True, ""),    # Step 4 → 5
        (True, ""),    # Step 5 → 6
        (True, "🎯 SNIPER TARGET HIT!"),  # Step 6 WIN - EXIT
    ]
    
    hand_num = 1
    for won, note in sequence:
        decision = BaccaratStrategist.get_next_decision(state)
        
        if decision['mode'] == PlayMode.STOPPED:
            break
        
        bet = decision['bet_amount']
        step = state.fibonacci_hunter_step_index + 1
        
        pnl_change = bet if won else -bet
        BaccaratStrategist.update_state_after_hand(state, won=won, pnl_change=pnl_change)
        
        print_hand(hand_num, step, bet, "WIN" if won else "LOSS", pnl_change, state.session_pnl, note)
        hand_num += 1
    
    print(f"\n📊 RESULT: Volatile Session Complete")
    print(f"   Total Profit: €{state.session_pnl:.0f}")
    print(f"   Hands Played: {hand_num - 1}")
    print(f"   Wins: {sum(1 for w, _ in sequence if w)}")
    print(f"   Losses: {sum(1 for w, _ in sequence if not w)}")
    print(f"   Status: {'✅ TARGET HIT' if state.mode == PlayMode.STOPPED else '⏸️  In Progress'}")


def scenario_5_comparison():
    """Compare base unit sizes"""
    print_header("SCENARIO 5: Base Unit Scaling Comparison")
    
    print("\nComparing perfect runs with different base units:\n")
    
    base_units = [50, 100, 200, 500]
    
    print(f"{'Base Unit':>10} | {'Seq Bets':>30} | {'Total Profit':>12}")
    print("-" * 60)
    
    for base in base_units:
        state = create_state(base_unit=base)
        sequence = [1, 1, 2, 3, 5, 8]
        bets = [base * x for x in sequence]
        total = sum(bets)
        
        bet_str = ", ".join([f"€{b}" for b in bets])
        print(f"€{base:>8} | {bet_str:>30} | €{total:>10,}")
    
    print("\n💡 Key Insight: Total profit = 20x base unit")
    print("   Example: €100 base = €2,000 profit per cycle")


def print_strategy_summary():
    """Print quick reference card"""
    print("\n" + "="*80)
    print("  FIBONACCI HUNTER - Quick Reference Card")
    print("="*80)
    
    print("\n📋 SEQUENCE: [1, 1, 2, 3, 5, 8] units")
    print("\n📈 PROGRESSION RULES:")
    print("   • WIN  → Advance to next step")
    print("   • LOSS → Hard reset to Step 1 (no gradual retreat)")
    print("   • TIE  → No change (remain at current step)")
    
    print("\n🎯 MODES:")
    print("   • SNIPER (STOP_SESSION):")
    print("     - Exit immediately after winning Step 6")
    print("     - Recommended for controlled sessions")
    print("     - Profit target: +20 base units")
    print("\n   • MARATHON (RESET_AND_CONTINUE):")
    print("     - Reset to Step 1 after Step 6 win")
    print("     - Continue playing for multiple cycles")
    print("     - Higher variance, higher potential")
    
    print("\n💰 PROFIT CALCULATION:")
    print("   Perfect Sequence: 1+1+2+3+5+8 = 20 base units")
    print("   €100 base = €2,000 per cycle")
    print("   €200 base = €4,000 per cycle")
    
    print("\n🛡️ SAFETY FEATURES:")
    print("   • Stop Loss: Overrides progression")
    print("   • PLAYER Only: Avoids commission decimals")
    print("   • Hard Reset: Prevents progressive bleeding")
    print("   • Session Exit: Locks in profits (Sniper mode)")
    
    print("\n⚠️  BANKROLL REQUIREMENT:")
    print("   Minimum: 30 base units (€3,000 @ €100 base)")
    print("   Recommended: 50 base units (€5,000 @ €100 base)")
    print("   Comfortable: 100 base units (€10,000 @ €100 base)")
    
    print("\n📊 STATISTICS:")
    print("   Win Rate Needed: 6 consecutive wins (1.56% @ 50/50)")
    print("   Max Single Bet: 8x base unit")
    print("   Avg Bet Size: ~3.3x base unit")
    print("   Risk/Reward: High variance, high reward")


def main():
    """Run all visual demonstrations"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  FIBONACCI HUNTER PROGRESSION - VISUAL DEMONSTRATION".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print_strategy_summary()
    
    scenario_1_perfect_run()
    scenario_2_reset_behavior()
    scenario_3_marathon_mode()
    scenario_4_volatile_session()
    scenario_5_comparison()
    
    print("\n" + "="*80)
    print("  END OF DEMONSTRATION")
    print("="*80)
    print("\n✅ All scenarios completed successfully")
    print("📚 For detailed guide, see: FIBONACCI_HUNTER_GUIDE.md")
    print("🧪 For testing, run: python test_fibonacci_hunter.py\n")


if __name__ == "__main__":
    main()
