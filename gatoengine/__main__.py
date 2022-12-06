from gatoengine.client.client import Client
from gatoengine.protocol.proto import QueryCurrRegionHttpRsp
from gatoengine.crypto.mhycrypt import decrypt, init_keys

import ec2b

import requests
import base64
import os
import importlib

TARGET_DISPATCH_URL = 'https://oseurodispatch.yuanshen.com/query_cur_region'
CHANNEL_ID = 1
SUB_CHANNEL_ID = 0
KEY_ID = 5

#Needs to be updated
DISPATCH_SEED = "b196f78211a8c830"
VERSION = "OSRELWin3.2.0"

FINAL_URL = f"{TARGET_DISPATCH_URL}?version={VERSION}&channel_id={CHANNEL_ID}&sub_channel_id={SUB_CHANNEL_ID}&dispatchSeed={DISPATCH_SEED}&key_id={KEY_ID}"

def main():
    init_keys("gatoengine/resources/keys")
    
    r = requests.get(FINAL_URL)
    key_id = KEY_ID
    respdata = r.json()
    respdec = decrypt(base64.b64decode(respdata['content']), key_id)

    proto = QueryCurrRegionHttpRsp()
    proto.parse(respdec)

    if proto.retcode == 0:
        client = Client((proto.region_info.gateserver_ip, proto.region_info.gateserver_port), KEY_ID, ec2b.derive(proto.client_secret_key))

        for module in os.listdir("gatoengine/client/handlers"):
            if module.endswith(".py"):
                imported_module = importlib.import_module(f'gatoengine.client.handlers.{module.replace(".py", "")}')
                client.add(imported_module.router)

        client.run()

if __name__ == "__main__":
    main()