from typing import Callable
from enum import Enum
import traceback

from betterproto import Message
from loguru import logger

from gatoengine.protocol.cmdid import CmdID
from gatoengine.network.kcp_socket import _Address, KcpSocket
from gatoengine.network.packet import Packet

from gatoengine.crypto import mhycrypt

Handler = Callable[["Client", Message], None]

class HandlerRouter:
    _handlers: dict[CmdID, Handler]

    def __init__(self):
        self._handlers = {}

    def add(self, router: "HandlerRouter"):
        self._handlers |= router._handlers

    def get(self, cmdid: CmdID) -> Handler | None:
        return self._handlers.get(cmdid)

    def __call__(self, cmdid: CmdID):
        def wrapper(handler: Handler):
            self._handlers[cmdid] = handler
            return handler
        return wrapper

class ConnectStatus(Enum):
    NOT_CONNECTED = 1
    CONNECTED = 2

class Client:
    def __init__(self, dst_server: _Address, key_id: int):
        self.router = HandlerRouter()
        self.dst_server = dst_server

        self.sock = KcpSocket()
        self.status = ConnectStatus.NOT_CONNECTED

        self.key_id = key_id
        self.client_seed = 0
        self.key = b''

    def add(self, router: HandlerRouter):
        self.router.add(router)

    def do_login(self):
        if handler := self.router.get(CmdID.GetPlayerTokenReq):
            handler(self, None) # Special handler for login only!
        else:
            logger.error(f'wtf you\'re missing GetPlayerTokenReq handler, check your code!')

    def handle(self, data: bytes):
        data = mhycrypt.xor(data, self.key)
        logger.debug(f'[S] {data.hex()}')
        try:
            packet = Packet().parse(data)
        except Exception:
            logger.error(f'Exception occured while parsing this data: {data.hex()}')
            logger.error(traceback.format_exc())
            return

        if handler := self.router.get(packet.cmdid):
            handler(self, packet.body)
        else:
            logger.warning(f'Unhandled packet: {packet.cmdid}')
            return

    def loop(self):
        if not self.sock.connect(self.dst_server):
            logger.error('[C] can\'t connect')
            return

        logger.info('[C] connected')
        self.status = ConnectStatus.CONNECTED

        while self.status == ConnectStatus.CONNECTED:
            data = self.sock.recv()
            self.handle(data)
        
        self.sock.close()
        return

    def send(self, msg: Message):
        packet = Packet(body=msg)
        self.send_raw(bytes(packet))

    def send_raw(self, data: bytes):
        data = mhycrypt.xor(data, self.key)
        self.sock.send(data)  

