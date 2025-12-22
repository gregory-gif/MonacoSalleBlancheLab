"""
Test script for Spice System v5.0
Validates core functionality and configuration
"""

from engine.spice_system import (
    SpiceEngine, SpiceType, SpiceFamily, SpiceRule, GlobalSpiceConfig,
    DEFAULT_SPICE_CONFIG, DEFAULT_GLOBAL_SPICE_CONFIG, SPICE_PATTERNS,
    create_default_engine
)

def test_spice_patterns():
    """Test that all 7 spice patterns are defined correctly"""
    print("=" * 60)
    print("TEST 1: Spice Pattern Definitions")
    print("=" * 60)
    
    expected_patterns = [
        "ZERO_LEGER_PATTERN",
        "JEU_ZERO_PATTERN",
        "ZERO_CROWN_PATTERN",
        "TIERS_PATTERN",
        "ORPHELINS_PATTERN",
        "ORPHELINS_PLEIN_PATTERN",
        "VOISINS_PATTERN"
    ]
    
    for pattern_id in expected_patterns:
        pattern = SPICE_PATTERNS.get(pattern_id)
        if pattern:
            print(f"✓ {pattern_id:25} | Cost: {pattern.unit_cost}u | Numbers: {len(pattern.numbers_covered)}")
        else:
            print(f"✗ {pattern_id} - MISSING!")
    
    print()

def test_default_config():
    """Test default spice configuration"""
    print("=" * 60)
    print("TEST 2: Default Configuration")
    print("=" * 60)
    
    print(f"Total spice types configured: {len(DEFAULT_SPICE_CONFIG)}")
    
    families = {"A_LIGHT": 0, "B_MEDIUM": 0, "C_PRESTIGE": 0}
    for spice_type, rule in DEFAULT_SPICE_CONFIG.items():
        families[rule.family.value] += 1
        print(f"  {spice_type.value:20} | Family: {rule.family.value:10} | Trigger: +{rule.trigger_pl_units}u")
    
    print(f"\nFamily Distribution:")
    for family, count in families.items():
        print(f"  {family}: {count} spices")
    
    print(f"\nGlobal Config:")
    print(f"  Max per session: {DEFAULT_GLOBAL_SPICE_CONFIG.max_total_spices_per_session}")
    print(f"  Max per spin: {DEFAULT_GLOBAL_SPICE_CONFIG.max_spices_per_spin}")
    print(f"  Disable if Caroline Step 4: {DEFAULT_GLOBAL_SPICE_CONFIG.disable_if_caroline_step4}")
    print()

def test_spice_engine():
    """Test SpiceEngine initialization and basic operations"""
    print("=" * 60)
    print("TEST 3: SpiceEngine Operations")
    print("=" * 60)
    
    engine = create_default_engine()
    print("✓ Engine created")
    
    engine.reset_session()
    print("✓ Session reset")
    
    # Test spice evaluation (none should fire with these params)
    fired = engine.evaluate_and_fire_spice(
        session_pl_units=5.0,  # Below any trigger
        spin_index=1,
        caroline_at_step4=False,
        session_start_bankroll=5000,
        current_bankroll=5050,
        stop_loss=500
    )
    
    if fired is None:
        print("✓ No spice fired (expected - P/L too low)")
    else:
        print(f"✗ Unexpected spice fired: {fired}")
    
    # Test with sufficient P/L
    engine.reset_spin()
    fired = engine.evaluate_and_fire_spice(
        session_pl_units=20.0,  # Above triggers
        spin_index=10,
        caroline_at_step4=False,
        session_start_bankroll=5000,
        current_bankroll=5200,
        stop_loss=500
    )
    
    if fired:
        print(f"✓ Spice fired: {fired.value}")
        
        # Test resolution
        pnl, won = engine.resolve_spice(fired, number=26, unit_bet_size=10.0)
        print(f"  Number: 26 | P/L: €{pnl:.2f} | Won: {won}")
    else:
        print("✗ Expected a spice to fire")
    
    stats = engine.get_statistics()
    print(f"✓ Statistics retrieved: {stats['total_spices_used']} spices used")
    print()

def test_caroline_safety():
    """Test Caroline safety lockout"""
    print("=" * 60)
    print("TEST 4: Caroline Safety Check")
    print("=" * 60)
    
    engine = create_default_engine()
    engine.reset_session()
    
    # Should not fire with Caroline at step 4
    fired = engine.evaluate_and_fire_spice(
        session_pl_units=30.0,
        spin_index=10,
        caroline_at_step4=True,  # LOCKOUT
        session_start_bankroll=5000,
        current_bankroll=5300,
        stop_loss=500
    )
    
    if fired is None:
        print("✓ Spice correctly blocked (Caroline at Step 4)")
    else:
        print(f"✗ Spice should not fire during Caroline stress: {fired}")
    
    print()

def test_global_cap():
    """Test global session cap (max 3 spices)"""
    print("=" * 60)
    print("TEST 5: Global Session Cap")
    print("=" * 60)
    
    engine = create_default_engine()
    engine.reset_session()
    
    spices_fired = []
    for spin in range(1, 100):
        engine.reset_spin()
        fired = engine.evaluate_and_fire_spice(
            session_pl_units=50.0,  # High P/L
            spin_index=spin,
            caroline_at_step4=False,
            session_start_bankroll=5000,
            current_bankroll=5500,
            stop_loss=500
        )
        if fired:
            spices_fired.append(fired)
            # Resolve it
            engine.resolve_spice(fired, number=10, unit_bet_size=10.0)
    
    total_fired = len(spices_fired)
    print(f"Spices fired over 100 spins: {total_fired}")
    
    if total_fired <= 3:
        print(f"✓ Global cap enforced (max 3, got {total_fired})")
    else:
        print(f"✗ Global cap violated! Expected ≤3, got {total_fired}")
    
    print()

def test_momentum_tp():
    """Test momentum TP boost"""
    print("=" * 60)
    print("TEST 6: Momentum TP Boost")
    print("=" * 60)
    
    engine = create_default_engine()
    
    # Test Family A/B boost
    initial_tp = 200.0
    new_tp_light = engine.apply_momentum_tp_boost(
        SpiceType.ZERO_LEGER, 
        initial_tp, 
        unit_size=10.0
    )
    print(f"Light Spice (Zéro Léger):")
    print(f"  Initial TP: €{initial_tp:.2f}")
    print(f"  New TP: €{new_tp_light:.2f}")
    print(f"  Boost: €{new_tp_light - initial_tp:.2f}")
    
    if (new_tp_light - initial_tp) == 200.0:
        print("  ✓ Correct boost (+20u = +€200)")
    else:
        print("  ✗ Incorrect boost")
    
    # Test Family C boost
    new_tp_prestige = engine.apply_momentum_tp_boost(
        SpiceType.VOISINS,
        initial_tp,
        unit_size=10.0
    )
    print(f"\nPrestige Spice (Voisins):")
    print(f"  Initial TP: €{initial_tp:.2f}")
    print(f"  New TP: €{new_tp_prestige:.2f}")
    print(f"  Boost: €{new_tp_prestige - initial_tp:.2f}")
    
    if (new_tp_prestige - initial_tp) == 400.0:
        print("  ✓ Correct boost (+40u = +€400)")
    else:
        print("  ✗ Incorrect boost")
    
    print()

def test_profit_window():
    """Test profit window boundaries"""
    print("=" * 60)
    print("TEST 7: Profit Window Logic")
    print("=" * 60)
    
    engine = create_default_engine()
    engine.reset_session()
    
    test_cases = [
        (10.0, False, "Below min (15u) - no spice eligible"),
        (15.0, True, "At min boundary - Light spices eligible"),
        (50.0, True, "Within window - Light/Medium spices"),
        (80.0, True, "At Light max boundary (80u)"),
        (85.0, True, "Above Light max - Prestige spices fire (max 100u)"),
        (105.0, False, "Above all maximums (>100u)"),
    ]
    
    for pl_units, should_fire, description in test_cases:
        engine.reset_session()
        engine.reset_spin()
        
        fired = engine.evaluate_and_fire_spice(
            session_pl_units=pl_units,
            spin_index=10,
            caroline_at_step4=False,
            session_start_bankroll=5000,
            current_bankroll=5000 + (pl_units * 10),
            stop_loss=500
        )
        
        result = f"FIRED ({fired.value})" if fired else "BLOCKED"
        expected = "FIRE" if should_fire else "BLOCK"
        status = "✓" if (fired is not None) == should_fire else "✗"
        
        print(f"{status} P/L: +{pl_units}u | {result:25} | {description}")
    
    print()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MONACO SALLE BLANCHE LAB - SPICE SYSTEM v5.0 TEST SUITE")
    print("=" * 60 + "\n")
    
    test_spice_patterns()
    test_default_config()
    test_spice_engine()
    test_caroline_safety()
    test_global_cap()
    test_momentum_tp()
    test_profit_window()
    
    print("=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)
