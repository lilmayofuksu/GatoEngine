from gatoengine.client.client import Client
from gatoengine.network.packet import Packet

from gatoengine.protocol.cmdid import CmdID
from gatoengine.protocol import proto

import asyncio, json, contextvars

from quart import Quart, request, websocket, Websocket, copy_current_app_context

app = Quart(__name__)

global client
client: Client = None

@app.route("/api/send_packet", methods=["POST"])
async def send_packet():
    packet: dict[str, object] = await request.json
    client.send_as_dict(packet["message"], packet["cmdid"])
    return "OK"

@app.websocket('/ws')
async def ws():
    async def send_data(message, ctx):
        await ctx.request_websocket.send(message.to_json())

    try:
        while True:
            data = await websocket.receive()
            if isinstance(data, str):
                message = json.loads(data)

                match message["cmd"]:
                    case "GetSocialInfo":
                        uid = message["data"]["uid"]
                        ws_context = websocket._LocalProxy__wrapped.get()
                        event_loop = asyncio.get_running_loop()

                        def callback(client: Client, message: proto.GetPlayerSocialDetailRsp):
                            asyncio.ensure_future(send_data(message, ws_context), loop=event_loop)
                            del client.router._handlers[CmdID.GetPlayerSocialDetailRsp]
                            return

                        client.router._handlers[CmdID.GetPlayerSocialDetailRsp] = callback
                        client.send(proto.GetPlayerSocialDetailReq(uid=uid))

    except asyncio.CancelledError:
        raise

def get_http_app():
    return app

def set_client(cl: Client):
    global client
    client = cl