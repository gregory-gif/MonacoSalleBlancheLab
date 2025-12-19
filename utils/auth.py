from nicegui import ui
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

# --- CONFIGURATION ---
# In a real scenario, use Environment Variables for these!
# But for now, you can hardcode them since the repo is private.
USERNAME = "admin"
PASSWORD = "password123" 

# A list of paths that don't need login (like the login page itself)
UNPROTECTED_ROUTES = {'/login'}

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Intercepts every request.
    If the user is not logged in, they are kicked to /login.
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path not in UNPROTECTED_ROUTES:
            # Check if the user has a 'authenticated' cookie
            if not request.session.get('authenticated'):
                return RedirectResponse('/login')
        return await call_next(request)

def setup_auth():
    """Defines the login page and logout logic."""
    
    @ui.page('/login')
    def login_page():
        def try_login():
            if username.value == USERNAME and password.value == PASSWORD:
                ui.context.client.request.session['authenticated'] = True
                ui.open('/') # Go to home
            else:
                ui.notify('Wrong credentials', type='negative')

        with ui.card().classes('absolute-center w-96 p-8 bg-slate-900 text-white'):
            ui.label('Salle Blanche Access').classes('text-2xl font-bold mb-4 text-center w-full')
            username = ui.input('Username').classes('w-full').props('dark')
            password = ui.input('Password', password=True).classes('w-full').props('dark')
            ui.button('Enter', on_click=try_login).classes('w-full mt-4 bg-amber-600 hover:bg-amber-500')

    # Add a logout button function you can use elsewhere
    # ui.link('Logout', '/logout') ... logic below handles session clear
