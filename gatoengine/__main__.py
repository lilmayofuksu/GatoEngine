from gatoengine.client.client import Client
from gatoengine.protocol.proto import QueryCurrRegionHttpRsp, QueryRegionListHttpRsp
from gatoengine.crypto.mhycrypt import decrypt, init_keys

import ec2b
import requests
from loguru import logger

import base64
import os, sys, asyncio
import importlib

from gatoengine.api.multiserver import get_http_app, set_client

DEFAULT_REGION_LIST_URL = "https://dispatchosglobal.yuanshen.com/query_region_list"

CHANNEL_ID = 1
SUB_CHANNEL_ID = 0
KEY_ID = 5

#Needs to be updated
DISPATCH_SEED = "db1e0cbda92030c3"
VERSION = "OSRELWin3.3.0"

#For Europe server
BACKUP_EC2B_SEED = base64.b64decode("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")
BACKUP_GATESERVER = ('47.245.143.151', 22102)

get_region_list_url = lambda x: f"{x}?version={VERSION}&channel_id={CHANNEL_ID}&sub_channel_id={SUB_CHANNEL_ID}"
get_dispatch_url = lambda x: f"{x}?version={VERSION}&channel_id={CHANNEL_ID}&sub_channel_id={SUB_CHANNEL_ID}&dispatchSeed={DISPATCH_SEED}&key_id={KEY_ID}"

def main():
    init_keys("gatoengine/resources/keys")
    
    if "--region-list" in sys.argv:
        query_region_url = get_region_list_url(sys.argv[sys.argv.index("--region-list") + 1])
    else:
        query_region_url = get_region_list_url(DEFAULT_REGION_LIST_URL)

    region_list_request = requests.get(query_region_url)
    proto = QueryRegionListHttpRsp().parse(base64.b64decode(region_list_request.text))

    if len(proto.region_list) > 0:
        logger.info(f"Found {len(proto.region_list)} available regions.")
        logger.info(f"Please select the target server:")

        for idx, region in enumerate(proto.region_list):
            logger.info(f"{idx} - {region.title} ({region.name})")

        if "--region" in sys.argv:
            region_name = sys.argv[sys.argv.index("--region") + 1]
            choice = proto.region_list.index(next(filter(lambda x: x.name == region_name, proto.region_list)))
            logger.info(f"Selected {proto.region_list[choice].title} ({proto.region_list[choice].name}) from arguments!")
        else:
            choice = int(input("Target server: "))

        if choice <= len(proto.region_list) - 1:
            region_request = requests.get(get_dispatch_url(proto.region_list[choice].dispatch_url))
            respdata = region_request.json()
            respdec = decrypt(base64.b64decode(respdata['content']), KEY_ID)

            proto = QueryCurrRegionHttpRsp().parse(respdec)

            if proto.retcode == 0:
                client = Client((proto.region_info.gateserver_ip, proto.region_info.gateserver_port), KEY_ID, ec2b.derive(proto.client_secret_key))
            else:
                logger.warning("Target server reported non zero retcode. Continuing with backup server\n")
                client = Client(BACKUP_GATESERVER, KEY_ID, ec2b.derive(BACKUP_EC2B_SEED))

            for module in os.listdir("gatoengine/client/handlers"):
                if module.endswith(".py"):
                    imported_module = importlib.import_module(f'gatoengine.client.handlers.{module.replace(".py", "")}')
                    client.add(imported_module.router)

            client.run()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                httpapp = get_http_app()
                set_client(client)

                loop.run_until_complete(httpapp.run_task())
            finally:
                loop.stop()
                loop.close()

        else:
            print("Invalid server selected.")
            exit()

if __name__ == "__main__":
    main()