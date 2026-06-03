"""
server_stats.py — Modul untuk web server dan dashboard statistik bot.

Menangani request ke endpoint `/` (dashboard HTML) dan `/ping` (health check).
"""
from aiohttp import web
from database import _get_history_collection, _get_jobs_collection


async def handle_root(request: web.Request) -> web.Response:
    """Root endpoint — menampilkan status bot dan stats dalam bentuk HTML."""
    try:
        history_coll = _get_history_collection()
        jobs_coll = _get_jobs_collection()
        
        history_count = await history_coll.count_documents({})
        jobs_count = await jobs_coll.count_documents({})
        pending_count = max(0, jobs_count - history_count)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>NyariKerja Broadcaster Stats</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; padding: 40px; }}
                .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }}
                h2 {{ text-align: center; color: #2c3e50; }}
                .stat {{ display: flex; justify-content: space-between; margin-bottom: 15px; font-size: 18px; }}
                .value {{ font-weight: bold; color: #27ae60; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>🚀 Bot Broadcaster Stats</h2>
                <div class="stat"><span>Status:</span> <span class="value" style="color: #2980b9;">🟢 Alive & Polling</span></div>
                <hr>
                <div class="stat"><span>Total Semua Loker:</span> <span class="value">{jobs_count}</span></div>
                <div class="stat"><span>Sudah di-Broadcast:</span> <span class="value">{history_count}</span></div>
                <div class="stat"><span>Dalam Antrean:</span> <span class="value" style="color: #e74c3c;">{pending_count}</span></div>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")
    except Exception as e:
        return web.Response(text=f"Bot Broadcaster is alive! (Stats error: {e})", content_type="text/plain")


async def handle_ping(request: web.Request) -> web.Response:
    """Ping endpoint — untuk Render uptime monitoring."""
    return web.Response(text="pong", content_type="text/plain")
