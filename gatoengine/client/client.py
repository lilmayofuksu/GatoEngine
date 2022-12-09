from typing import Callable
from enum import Enum

import traceback
import datetime
import threading
import os
import json
import random

from betterproto import Message
from loguru import logger

from gatoengine.protocol.cmdid import CmdID
from gatoengine.protocol.proto import PingReq

from gatoengine.network.kcp_socket import _Address, KcpSocket
from gatoengine.network.packet import Packet

from gatoengine.crypto import mhycrypt

Handler = Callable[["Client", Message], None]
PRINT_PACKETS = False

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
    LOGGED_IN = 3

class Client:
    def __init__(self, dst_server: _Address, key_id: int, initial_key: bytes):
        self.router = HandlerRouter()

        self.dst_server = dst_server

        self.sock = KcpSocket()
        self.status = ConnectStatus.NOT_CONNECTED

        self.hoyouid = ""
        self.combo_token = ""

        self.client_seed = 0
        self.key_id = key_id
        self.key = initial_key
        self.report_data = b''

        self.starttime = datetime.datetime.now()
        self.pingtime = datetime.datetime.now()

        self.thread: threading.Thread = None

        if not os.path.isfile("gatoengine/resources/private_info.json"):
            raise Exception("Can't find private_info.json! Make sure to edit the template to add login informations.")
        else:
            with open("gatoengine/resources/private_info.json", "r") as f:
                config = json.load(f)

                self.hoyouid = config["hoyoUid"]
                self.combo_token = config["comboToken"]


    def add(self, router: HandlerRouter):
        self.router.add(router)
    
    def run(self):
        #self.loop()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def do_login(self):
        if handler := self.router.get(CmdID.GetPlayerTokenReq):
            handler(self, None) # Special handler for login only!
        else:
            logger.error(f'wtf you\'re missing GetPlayerTokenReq handler, check your code!')

    def handle(self, data: bytes):
        data = mhycrypt.xor(data, self.key)

        try:
            packet = Packet().parse(data)
        except Exception:
            logger.error(f'Exception occured while parsing packet: {data.hex()}')
            logger.error(traceback.format_exc())
            return
        if PRINT_PACKETS:
            logger.debug(f'[S] {packet.head.to_dict()}, {packet.body.to_dict()}')

        if handler := self.router.get(packet.cmdid):
            logger.debug(f'[S] {packet.cmdid}:{packet.body.__class__.__name__}')
            handler(self, packet.body)
        else:
            logger.warning(f'Unhandled packet {packet.cmdid}:{packet.body.__class__.__name__}!')
            return

    def loop(self):
        if not self.sock.connect(self.dst_server):
            logger.error('[C] can\'t connect')
            return

        logger.info('[C] connected')
        self.status = ConnectStatus.CONNECTED

        self.do_login()

        while self.status.value > 1:
            data = self.sock.recv()

            if (timedelta := (datetime.datetime.now() - self.pingtime)).seconds > 6:
                self.pingtime = datetime.datetime.now()
                pingreq = PingReq(client_time=round(self.pingtime.timestamp()), ue_time=timedelta.total_seconds())

                if self.report_data != b'':
                    pingreq.sc_data = self.report_data
                    logger.debug(f"Sending SecurityChannel data!")
                    self.report_data = b''

                self.send(pingreq)

            if data:
                self.handle(data)
        
        self.sock.close()
        return

    def send_as_dict(self, msg: dict, cmdid: int):
        packet = Packet()
        packet.cmdid = CmdID(cmdid)
        packet.parse_from_dict(msg)
        self.send_packet(packet)

    def send(self, msg: Message):
        packet = Packet(body=msg)
        self.send_packet(packet)

    def send_packet(self, packet: Packet):
        logger.debug(f'[C] {packet.cmdid}:{packet.body.__class__.__name__}')
        if PRINT_PACKETS:
            logger.debug(f'[C] {packet.head.to_dict()}, {packet.body.to_dict()}')
        packet.head.sent_ms = round(datetime.datetime.now().timestamp())
        self.send_raw(bytes(packet))

    def send_raw(self, data: bytes):
        data = mhycrypt.xor(data, self.key)
        self.sock.send(data)  

