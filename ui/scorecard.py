from nicegui import ui
from engine.strategy_rules import SessionState, BaccaratStrategist, PlayMode, BetStrategy, StrategyOverrides
from engine.tier_params import get_tier_for_ga, generate_tier_map
from utils.persistence import load_profile, save_profile, log_session_result

# --- LIVE SESSION MANAGER ---
class LiveSessionManager:
    def __init__(self):
        self.state = None
        self.history = [] 
        self.banker_wins = 0
        self.player_wins = 0
        self.ties = 0
        self.start_ga = 0.0
        self.current_ga = 0.0
        self.active_strategy_name = "Manual"

    def start_session(self, strategy_name: str, config: dict, current_profile_ga: float):
        self.active_strategy_name = strategy_name
        self.start_ga = current_profile_ga
        self.current_ga = current_profile_ga
        self.history = []
        self.banker_wins = 0; self.player_wins = 0; self.ties = 0

        # Build Objects
        mode = config.get('tac_mode', 'Standard')
        safety = config.get('tac_safety', 25)
        tier_map = generate_tier_map(safety, mode=mode)
        initial_tier = get_tier_for_ga(self.current_ga, tier_map, 1, mode)

        overrides = StrategyOverrides(
            iron_gate_limit=config.get('tac_iron', 3),
            stop_loss_units=config.get('risk_stop', 10),
            profit_lock_units=config.get('risk_prof', 10),
            press_trigger_wins=config.get('tac_press', 1),
            press_depth=config.get('tac_depth', 3),
            ratchet_enabled=config.get('risk_ratch', False),
            ratchet_mode=config.get('risk_ratch_mode', 'Standard'),
            shoes_per_session=config.get('tac_shoes', 3),
            bet_strategy=BetStrategy.BANKER if config.get('tac_bet', 'Banker') == 'Banker' else BetStrategy.PLAYER,
            penalty_box_enabled=config.get('tac_penalty', True)
        )
        self.state = SessionState(tier=initial_tier, overrides=overrides)
        
    def process_result(self, result: str):
        if not self.state: return
        
        # 1. What did the Engine WANT us to do?
        decision = BaccaratStrategist.get_next_decision(self.state)
        bet_amt = decision['bet_amount']
        target = self.state.overrides.bet_strategy 
        
        # 2. Did we win?
        won = False
        pnl_change = 0.0
        
        if result != 'T':
            if (target == BetStrategy.BANKER and result == 'B') or \
               (target == BetStrategy.PLAYER and result == 'P'):
                won = True
                pnl_change = bet_amt # Engine applies commission inside update_state
            else:
                won = False
                pnl_change = -bet_amt

            # 3. Update Engine
            BaccaratStrategist.update_state_after_hand(self.state, won, pnl_change)
            
            # 4. Update Wallet (Only if Real)
            if not self.state.is_in_virtual_mode:
                self.current_ga += self.state.session_pnl - (self.current_ga - self.start_ga) 
                # Re-sync GA with State PnL to be safe (Engine handles commission math)
                self.current_ga = self.start_ga + self.state.session_pnl

        # 5. Stats
        self.history.append(result)
        if result == 'B': self.banker_wins += 1
        elif result == 'P': self.player_wins += 1
        else: self.ties += 1

    def get_advice(self):
        if not self.state: return {'mode': PlayMode.STOPPED, 'text': 'SELECT STRATEGY', 'color': 'bg-slate-700', 'sub': ''}
        
        decision = BaccaratStrategist.get_next_decision(self.state)
        
        if decision['mode'] == PlayMode.STOPPED:
            return {'mode': PlayMode.STOPPED, 'text': decision['reason'], 'color': 'bg-red-600', 'sub': 'SESSION OVER'}
            
        if decision['reason'] == 'VIRTUAL (OBSERVING)':
            return {'mode': PlayMode.PLAYING, 'text': 'VIRTUAL MODE', 'color': 'bg-yellow-600', 'sub': 'DO NOT BET (Wait for Virtual Win)'}
            
        target_str = self.state.overrides.bet_strategy.name
        amt = decision['bet_amount']
        return {'mode': PlayMode.PLAYING, 'text': f"BET €{amt:.0f} {target_str}", 'color': 'bg-green-600', 'sub': 'LIVE ACTION'}

    def save_and_quit(self):
        if not self.state: return
        # Update Profile
        profile = load_profile()
        profile['ga'] = self.current_ga
        save_profile(profile)
        # Log Session
        log_session_result(self.start_ga, self.current_ga, shoes_played=1)

session = LiveSessionManager()

def show_scorecard():
    
    def refresh_advice():
        advice = session.get_advice()
        card_advice.classes(remove='bg-slate-700 bg-red-600 bg-yellow-600 bg-green-600')
        card_advice.classes(add=advice['color'])
        lbl_advice_main.set_text(advice['text'])
        lbl_advice_sub.set_text(advice['sub'])
        
        total = len(session.history)
        if total > 0:
            pb = (session.banker_wins/total)*100
            pp = (session.player_wins/total)*100
            pt = (session.ties/total)*100
        else: pb=pp=pt=0
        
        lbl_stats.set_text(f"B: {session.banker_wins} ({pb:.0f}%) | P: {session.player_wins} ({pp:.0f}%) | T: {session.ties}")
        
        pnl = session.current_ga - session.start_ga
        color = "text-green-400" if pnl >= 0 else "text-red-400"
        lbl_pnl.set_text(f"PnL: €{pnl:,.0f}")
        lbl_pnl.classes(remove="text-green-400 text-red-400"); lbl_pnl.classes(add=color)
        lbl_ga.set_text(f"Bal: €{session.current_ga:,.0f}")
        
        bead_plate.clear()
        with bead_plate:
            for res in session.history[-20:]: 
                c = 'bg-red-500' if res == 'B' else 'bg-blue-500' if res == 'P' else 'bg-green-500'
                ui.label(res).classes(f'w-8 h-8 rounded-full {c} text-white flex items-center justify-center font-bold text-xs')

    def handle_input(res):
        if not session.state: ui.notify('Start a session first!', type='warning'); return
        session.process_result(res)
        refresh_advice()

    def start_selected_strategy():
        strat_name = select_strat.value
        if not strat_name: return
        profile = load_profile()
        config = profile.get('saved_strategies', {}).get(strat_name)
        if not config: ui.notify('Strategy config error', type='negative'); return
        session.start_session(strat_name, config, profile.get('ga', 2000))
        refresh_advice()
        dialog_strat.close()
        ui.notify(f'Session Started: {strat_name}', type='positive')

    def finish_session():
        session.save_and_quit()
        ui.notify('Session Saved', type='info')
        ui.navigate.to('/') 

    # --- UI ---
    with ui.column().classes('w-full max-w-xl mx-auto p-4 gap-4'):
        with ui.card().classes('w-full p-6 items-center justify-center bg-slate-700 transition-colors duration-300') as card_advice:
            lbl_advice_main = ui.label('SELECT STRATEGY').classes('text-3xl font-black text-white text-center')
            lbl_advice_sub = ui.label('').classes('text-sm font-bold text-white/80 uppercase tracking-widest')

        with ui.row().classes('w-full justify-between px-2'):
            lbl_ga = ui.label('Bal: €---').classes('text-slate-400 font-mono')
            lbl_pnl = ui.label('PnL: €0').classes('text-slate-400 font-mono')
            
        with ui.grid(columns=3).classes('w-full gap-4'):
            with ui.button(on_click=lambda: handle_input('P')).classes('h-24 bg-blue-700 rounded-xl shadow-[0_4px_0_rgb(29,78,216)] active:shadow-none active:translate-y-1'):
                ui.label('PLAYER').classes('text-xl font-bold text-white')
            with ui.button(on_click=lambda: handle_input('T')).classes('h-24 bg-green-700 rounded-xl shadow-[0_4px_0_rgb(21,128,61)] active:shadow-none active:translate-y-1'):
                ui.label('TIE').classes('text-xl font-bold text-white')
            with ui.button(on_click=lambda: handle_input('B')).classes('h-24 bg-red-700 rounded-xl shadow-[0_4px_0_rgb(185,28,28)] active:shadow-none active:translate-y-1'):
                ui.label('BANKER').classes('text-xl font-bold text-white')

        with ui.card().classes('w-full bg-slate-800 p-3 min-h-[60px]'): bead_plate = ui.row().classes('flex-wrap gap-1')
        lbl_stats = ui.label('B: 0 | P: 0 | T: 0').classes('text-xs text-slate-500 w-full text-center')

        with ui.row().classes('w-full justify-center gap-4 mt-4'):
            ui.button('START SESSION', on_click=lambda: dialog_strat.open()).props('icon=play_arrow color=yellow text-color=black')
            ui.button('CASH OUT', on_click=finish_session).props('icon=save color=slate')

    with ui.dialog() as dialog_strat, ui.card().classes('bg-slate-800 text-white min-w-[300px]'):
        ui.label('Choose Protocol').classes('text-lg font-bold mb-4')
        prof = load_profile()
        strats = list(prof.get('saved_strategies', {}).keys())
        select_strat = ui.select(strats, label='Strategy').classes('w-full mb-6')
        ui.button('INITIALIZE', on_click=start_selected_strategy).props('color=green w-full')
