import asyncio
import gc
import microdot
import logging

from logger import Logger
from logic import Logic
from utils import Utils

log = logging.getLogger("SERVER")
log.setLevel(logging.DEBUG)

app = microdot.Microdot()


@app.get("/")
async def index(_request):
    gc.collect()
    return microdot.send_file("code/index.html")


@app.get("/log/subscribe")
async def log_subscribe(_request):
    gc.collect()
    stream_id = Logger.register_web_stream()
    return {"stream_id": stream_id}


@app.get("/log/stream/<stream_id>")
async def log_endpoint(_request, stream_id):
    gc.collect()
    stream_id = int(stream_id)
    data = await Logger.fetch_web_stream(stream_id)
    return {"data": data, "status": "ok" if data is not None else "expired"}


@app.get("/toggle_ac")
async def toggle_ac(_request):
    gc.collect()
    log.info("Toggle AC requested")
    state = await Logic.delta2.get_ac_enabled()
    log.info("AC was %d, toggling to %d...", state, not state)
    await Logic.delta2.set_ac_enabled(not state)
    await asyncio.sleep(5)
    log.info("AC is now %d", await Logic.delta2.get_ac_enabled())


@app.get("/toggle_relay")
async def toggle_relay(_request):
    gc.collect()
    log.info("Toggle relay requested")
    state = await Utils.relay_enabled()
    log.info("Relay was %d, toggling to %d...", state, not state)
    await Utils.relay_enabled(not state)
    log.info("Relay is now %d", await Utils.relay_enabled())


@app.get("/shutdown_server")
async def shutdown_server(request):
    gc.collect()
    log.info("Shutdown requested")
    request.app.shutdown()
    return "ok"


@app.get("/reset_machine/soft")
async def reset_machine_soft(_request):
    log.info("Machine soft reset requested")
    await Utils.reset_machine(hard=False)


@app.get("/reset_machine/hard")
async def reset_machine_hard(_request):
    log.info("Machine hard reset requested")
    await Utils.reset_machine(hard=True)


class Server:
    port = 80

    @classmethod
    async def run(cls):
        log.info("Running webserver on port %d...", cls.port)
        await app.start_server(host="0.0.0.0", port=cls.port, debug=False)
        await asyncio.sleep(3)
        log.info("Server stopped")
        gc.collect()
