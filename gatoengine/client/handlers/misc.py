from gatoengine.protocol.proto import PingRsp, PlayerTimeNotify, ServerAnnounceNotify
from gatoengine.protocol.cmdid import CmdID
from gatoengine.client.client import Client, HandlerRouter
from gatoengine.crypto import mhycrypt


import random, base64, json, datetime

from loguru import logger
import humanize

router = HandlerRouter()

@router(CmdID.PingRsp)
def ping_rsp(client: Client, msg: PingRsp):
    return

@router(CmdID.PlayerTimeNotify)
def ping_rsp(client: Client, msg: PlayerTimeNotify):
    return

@router(CmdID.ServerAnnounceNotify)
def server_announce(client: Client, msg: ServerAnnounceNotify):
    logger.warning(f'Servers will go down in {humanize.precisedelta(datetime.datetime.fromtimestamp(msg.announce_data_list[0].end_time) - datetime.datetime.now(), minimum_unit="minutes", format="%0.f")}!')
    return