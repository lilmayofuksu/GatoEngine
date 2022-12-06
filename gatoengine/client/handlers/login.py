from gatoengine.protocol import proto
from gatoengine.protocol.cmdid import CmdID

from gatoengine.client.client import Client, HandlerRouter

router = HandlerRouter()

@router(CmdID.GetPlayerTokenReq)
def get_player_token_req(client: Client, _):
    ...