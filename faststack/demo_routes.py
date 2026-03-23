"""
FastUI Demo Routes for FastStack
Demonstrates HTMX integration with HTML fragment responses
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
import random

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("", response_class=HTMLResponse)
async def demo_page(request: Request):
    """Main demo page"""
    from faststack.config import settings
    return request.app.state.templates.TemplateResponse(
        "demo/index.html",
        {"request": request, "settings": settings}
    )


# ============ HTMX Fragment Endpoints ============

@router.get("/api/users", response_class=HTMLResponse)
async def get_users_fragment(request: Request):
    """Returns HTML fragment with user list"""
    users = [
        {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "role": "Admin"},
        {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "role": "User"},
        {"id": 3, "name": "Carol White", "email": "carol@example.com", "role": "Editor"},
        {"id": 4, "name": "David Brown", "email": "david@example.com", "role": "User"},
    ]
    
    html = '''
    <div class="space-y-2">
        <h3 class="font-bold text-gray-800 mb-3"><i class="fas fa-users mr-2"></i>Users</h3>
    '''
    for user in users:
        html += f'''
        <div class="flex items-center justify-between p-3 bg-white rounded border hover:shadow-sm transition">
            <div>
                <div class="font-medium">{user["name"]}</div>
                <div class="text-sm text-gray-500">{user["email"]}</div>
            </div>
            <span class="px-2 py-1 text-xs rounded-full {'bg-indigo-100 text-indigo-700' if user['role'] == 'Admin' else 'bg-gray-100 text-gray-700'}">{user["role"]}</span>
        </div>
        '''
    html += '</div>'
    return HTMLResponse(content=html)


@router.get("/api/stats", response_class=HTMLResponse)
async def get_stats_fragment(request: Request):
    """Returns HTML fragment with statistics"""
    stats = {
        "total_users": random.randint(100, 500),
        "active_sessions": random.randint(20, 80),
        "requests_today": random.randint(1000, 5000),
        "avg_response_time": random.uniform(45, 150),
    }
    
    html = f'''
    <div>
        <h3 class="font-bold text-gray-800 mb-3"><i class="fas fa-chart-line mr-2"></i>Statistics</h3>
        <div class="grid grid-cols-2 gap-3">
            <div class="p-3 bg-indigo-50 rounded text-center">
                <div class="text-2xl font-bold text-indigo-600">{stats["total_users"]}</div>
                <div class="text-sm text-gray-600">Total Users</div>
            </div>
            <div class="p-3 bg-green-50 rounded text-center">
                <div class="text-2xl font-bold text-green-600">{stats["active_sessions"]}</div>
                <div class="text-sm text-gray-600">Active Sessions</div>
            </div>
            <div class="p-3 bg-blue-50 rounded text-center">
                <div class="text-2xl font-bold text-blue-600">{stats["requests_today"]:,}</div>
                <div class="text-sm text-gray-600">Requests Today</div>
            </div>
            <div class="p-3 bg-yellow-50 rounded text-center">
                <div class="text-2xl font-bold text-yellow-600">{stats["avg_response_time"]:.1f}ms</div>
                <div class="text-sm text-gray-600">Avg Response</div>
            </div>
        </div>
    </div>
    '''
    return HTMLResponse(content=html)


@router.get("/api/notifications", response_class=HTMLResponse)
async def get_notifications_fragment(request: Request):
    """Returns HTML fragment with notifications"""
    notifications = [
        {"type": "warning", "icon": "exclamation-triangle", "message": "Server load at 85%"},
        {"type": "success", "icon": "check-circle", "message": "Backup completed successfully"},
        {"type": "info", "icon": "info-circle", "message": "New user registered"},
    ]
    
    colors = {
        "warning": "yellow",
        "success": "green",
        "info": "blue"
    }
    
    html = '''
    <div>
        <h3 class="font-bold text-gray-800 mb-3"><i class="fas fa-bell mr-2"></i>Notifications</h3>
        <div class="space-y-2">
    '''
    for notif in notifications:
        color = colors[notif["type"]]
        html += f'''
        <div class="flex items-center gap-3 p-3 bg-{color}-50 rounded border border-{color}-200">
            <i class="fas fa-{notif["icon"]} text-{color}-500"></i>
            <span class="text-{color}-700">{notif["message"]}</span>
        </div>
        '''
    html += '</div></div>'
    return HTMLResponse(content=html)


@router.get("/api/time", response_class=HTMLResponse)
async def get_server_time(request: Request):
    """Returns current server time"""
    now = datetime.now()
    return HTMLResponse(content=now.strftime("%Y-%m-%d %H:%M:%S"))


@router.post("/api/submit", response_class=HTMLResponse)
async def submit_form(request: Request):
    """Handle form submission"""
    form_data = await request.form()
    message = form_data.get("message", "")
    
    html = f'''
    <div class="p-4 bg-green-50 rounded border border-green-200">
        <div class="flex items-center gap-2 text-green-700">
            <i class="fas fa-check-circle"></i>
            <span class="font-medium">Message received!</span>
        </div>
        <p class="mt-2 text-gray-700">You sent: "{message}"</p>
        <p class="text-sm text-gray-500 mt-1">Submitted at {datetime.now().strftime("%H:%M:%S")}</p>
    </div>
    '''
    return HTMLResponse(content=html)


@router.get("/api/lazy-content", response_class=HTMLResponse)
async def get_lazy_content(request: Request):
    """Returns content for lazy loading"""
    html = '''
    <div class="p-4 bg-indigo-50 rounded-lg text-center">
        <h4 class="text-lg font-bold text-indigo-800">🚀 Lazy Loaded!</h4>
        <p class="text-indigo-700">This content was loaded when you scrolled to it.</p>
        <p class="text-sm text-indigo-500 mt-2">Server response time: ~50ms</p>
    </div>
    '''
    return HTMLResponse(content=html)
