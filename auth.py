from nicegui import ui, app
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

# --- CONFIGURATION ---
USERNAME = "admin"
PASSWORD = "password123" 

# Routes that anyone can visit
UNPROTECTED_ROUTES = {'/login'}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Check if the session has the 'authenticated' key
        # We access request.session directly, NOT app.storage.user
        if not request.session.get('authenticated'):
            # 2. If not logged in, and trying to access a protected page...
            if request.url.path not in UNPROTECTED_ROUTES and not request.url.path.startswith('/_nicegui'):
                # 3. Redirect to login
                return RedirectResponse('/login')
        
        return await call_next(request)

def setup_auth():
    @ui.page('/login')
    def login_page():
        def try_login():
            if username.value == USERNAME and password.value == PASSWORD:
                # We can use app.storage.user here because we are INSIDE a page
                app.storage.user['authenticated'] = True
                ui.open('/') 
            else:
                ui.notify('Access Denied', type='negative')

        with ui.column().classes('absolute-center w-full max-w-sm p-8 bg-slate-900 rounded-xl shadow-2xl border border-slate-700'):
            ui.label('Salle Blanche Lab').classes('text-2xl font-bold text-white mb-2 self-center')
            ui.label('Restricted Access').classes('text-slate-500 text-sm mb-6 self-center')
            
            username = ui.input('Username').props('dark outlined').classes('w-full')
            password = ui.input('Password', password=True).props('dark outlined').classes('w-full')
            
            ui.button('UNLOCK', on_click=try_login).classes('w-full mt-6 bg-amber-600 hover:bg-amber-500 text-white font-bold')

    @ui.page('/logout')
    def logout():
        app.storage.user['authenticated'] = False
        ui.open('/login')
