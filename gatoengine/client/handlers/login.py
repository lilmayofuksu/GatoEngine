from gatoengine.protocol.proto import GetPlayerTokenReq, GetPlayerTokenRsp, PlayerLoginReq, PlayerLoginRsp
from gatoengine.protocol.cmdid import CmdID
from gatoengine.client.client import Client, HandlerRouter, ConnectStatus
from gatoengine.crypto import mhycrypt

import random, base64, json

from loguru import logger

router = HandlerRouter()

@router(CmdID.GetPlayerTokenReq)
def get_player_token_req(client: Client, _):
    msg = GetPlayerTokenReq()

    client.client_seed = random.randint(2147483647, 9223372036854775807)
    msg.client_rand_key = base64.b64encode(mhycrypt.encrypt(data=int.to_bytes(client.client_seed, byteorder='big', length=8), key_id=client.key_id, is_sign=True)).decode()

    msg.account_token = client.combo_token
    msg.account_uid = client.hoyouid
    msg.key_id = client.key_id

    msg.channel_id = 1
    msg.platform_type = 3 #PC
    msg.account_type = 1

    client.send(msg)

@router(CmdID.GetPlayerTokenRsp)
def get_player_token_rsp(client: Client, msg: GetPlayerTokenRsp):
    server_seed_bytes = mhycrypt.decrypt(base64.b64decode(msg.server_rand_key), msg.key_id)
    server_seed = int.from_bytes(server_seed_bytes, byteorder='big', signed=False)

    client.key = mhycrypt.new_key(server_seed ^ client.client_seed)
    
    if (security_cmd_resp := mhycrypt.solve_security_cmd(msg.security_cmd_buffer)) != b'':
        loginreq = PlayerLoginReq()
        loginreq.security_cmd_reply = security_cmd_resp

        with open("gatoengine/resources/client_info.json", "r") as f:
            loginreq.from_json(f.read())
        
        loginreq.client_verison_hash = mhycrypt.gen_version_hash(loginreq.client_version, msg.client_version_random_key)
        loginreq.language_type = 1
        loginreq.account_type = 1
        loginreq.token = client.combo_token

        client.send(loginreq)
    else:
        logger.error(f'Failed to generate security cmd response! Stopping the client...')
        client.status = ConnectStatus.NOT_CONNECTED
        return

@router(CmdID.PlayerLoginRsp)
def player_login_rsp(client: Client, msg: PlayerLoginRsp):
    if msg.is_sc_open:
        logger.debug(f"Generating SecurityChannel data!")
        client.report_data = mhycrypt.generate_sc_data(msg.sc_info, ["catch except rertetewq2 task"])
        
    return