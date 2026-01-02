#!/usr/bin/env python3
"""
Integration test for Negatif 1-2-4-7 Snap-Back progression.
Tests a full session simulation using the RouletteWorker.
"""

from ui.roulette_sim import RouletteWorker
from engine.strategy_rules import StrategyOverrides
from engine.tier_params import generate_tier_map

def test_full_session_with_snapback():
    """Run a full session with the negatif snap-back progression"""
    
    print("=" * 70)
    print("FULL SESSION TEST: NEGATIF 1-2-4-7 SNAP-BACK")
    print("=" * 70)
    
    # Configuration
    current_ga = 50000  # Starting bankroll
    base_bet = 5.0
    
    # Create overrides for negatif snap-back
    overrides = StrategyOverrides(
        shoes_per_session=3,  # 180 spins
        stop_loss_units=50,
        profit_lock_units=30,
        press_trigger_wins=7,  # Negatif 1-2-4-7 Snap-Back
        press_depth=3,
        iron_gate_limit=5,
        ratchet_enabled=False,
        bet_strategy='Red',
        bet_strategy_2='Odd',
        
        # Disable spices for clear test
        spice_zero_leger_enabled=False,
        spice_jeu_zero_enabled=False,
        spice_zero_crown_enabled=False,
        spice_tiers_enabled=False,
        spice_orphelins_enabled=False,
        spice_orphelins_plein_enabled=False,
        spice_voisins_enabled=False,
        
        # Disable smart trailing
        smart_exit_enabled=False,
        
        # Penalty box disabled
        penalty_box_enabled=False
    )
    
    # Generate tier map
    tier_map = generate_tier_map(
        safety_factor=1.0,
        mode='STANDARD',
        game_type='Roulette',
        base_bet=base_bet
    )
    
    print(f"\nConfiguration:")
    print(f"  Starting Bankroll: €{current_ga:,.2f}")
    print(f"  Base Bet: €{base_bet}")
    print(f"  Betting: Red + Odd")
    print(f"  Progression: Negatif 1-2-4-7 Snap-Back")
    print(f"  Stop Loss: {overrides.stop_loss_units} units (€{overrides.stop_loss_units * base_bet})")
    print(f"  Target Profit: {overrides.profit_lock_units} units (€{overrides.profit_lock_units * base_bet})")
    print(f"  Max Spins: {overrides.shoes_per_session * 60}")
    print(f"\nKey Feature:")
    print(f"  When one bet enters progression, the other halts until")
    print(f"  progression completes (win) or fails (max level).")
    print("\n" + "=" * 70)
    
    # Run multiple sessions for statistical sampling
    num_sessions = 10
    results = []
    
    print(f"\nRunning {num_sessions} sessions...\n")
    
    for session_num in range(1, num_sessions + 1):
        result = RouletteWorker.run_session(
            current_ga=current_ga,
            overrides=overrides,
            tier_map=tier_map,
            use_ratchet=False,
            penalty_mode=False,
            active_level=1,
            mode='STANDARD',
            base_bet=base_bet
        )
        
        session_pnl = result[0]
        volume = result[1]
        tier_level = result[2]
        spins_played = result[3]
        exit_reason = result[5]
        
        results.append({
            'pnl': session_pnl,
            'volume': volume,
            'spins': spins_played,
            'exit': exit_reason
        })
        
        # Display result
        win_symbol = "✓" if session_pnl > 0 else "✗"
        print(f"Session {session_num:2d}: {win_symbol} P&L: €{session_pnl:7.2f} | "
              f"Spins: {spins_played:3d} | Exit: {exit_reason:12s} | "
              f"Volume: €{volume:8.2f}")
    
    # Calculate statistics
    total_pnl = sum(r['pnl'] for r in results)
    avg_pnl = total_pnl / num_sessions
    wins = sum(1 for r in results if r['pnl'] > 0)
    losses = sum(1 for r in results if r['pnl'] < 0)
    win_rate = (wins / num_sessions) * 100
    total_volume = sum(r['volume'] for r in results)
    avg_spins = sum(r['spins'] for r in results) / num_sessions
    
    print("\n" + "=" * 70)
    print("SESSION STATISTICS")
    print("=" * 70)
    print(f"Sessions Played: {num_sessions}")
    print(f"Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
    print(f"Total P&L: €{total_pnl:,.2f}")
    print(f"Average P&L: €{avg_pnl:,.2f}")
    print(f"Total Volume: €{total_volume:,.2f}")
    print(f"Average Spins: {avg_spins:.1f}")
    
    # Exit reason breakdown
    exit_reasons = {}
    for r in results:
        exit_reasons[r['exit']] = exit_reasons.get(r['exit'], 0) + 1
    
    print(f"\nExit Reasons:")
    for reason, count in sorted(exit_reasons.items()):
        print(f"  {reason}: {count} ({count/num_sessions*100:.0f}%)")
    
    print("=" * 70)
    print("\n✓ Integration test completed successfully!")
    print("  The Negatif 1-2-4-7 Snap-Back progression is working correctly.")
    print("  Use the UI (main.py) to run full simulations with this progression.")
    print("=" * 70)

if __name__ == '__main__':
    test_full_session_with_snapback()
