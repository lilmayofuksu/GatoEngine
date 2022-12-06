from itertools import cycle
from typing import Tuple
import os
import base64

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

from .mt64 import mt64
import mhycrypto

private_keys = {}
signing_keys = {}

def init_keys(path: str):
    for key_path in os.listdir(path):
        if key_path.endswith("_sign.pem"):
            with open(key_path, "r") as f:
                key_id = os.path.basename(key_path)[:1]
                signing_keys[key_id] = RSA.import_key(f.read())
        else:
            with open(key_path, "r") as f:
                key_id = os.path.basename(key_path)[:1]
                private_keys[key_id] = RSA.import_key(f.read())

def new_key(seed: int) -> bytes:
    mt = mt64()
    mt.seed(seed)

    mt.seed(mt.int64())
    mt.int64()

    return bytes(byte for _ in range(512) for byte in mt.int64().to_bytes(8, "big"))

def xor(data: bytes, key: bytes) -> bytes:
    return bytes(v ^ k for (v, k) in zip(data, cycle(key)))

def decrypt(data: bytes, key_id) -> bytes:
    key = private_keys[key_id]
    dec = PKCS1_v1_5.new(key)

    chunk_size = 256
    out = b''

    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        out += dec.decrypt(chunk, None)

    return out

def sign(message, key_id):
    signer = pkcs1_15.new(signing_keys[key_id])
    digest = SHA256.new(message)
    return signer.sign(digest)

def encrypt(data: bytes, key_id, is_sign = False) -> bytes:
    if is_sign:
        key = signing_keys[key_id]
    else:
        key = private_keys[key_id]
    enc = PKCS1_v1_5.new(key)

    chunk_size = 256 - 11
    out = b''

    if len(data) > chunk_size:
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            out += enc.encrypt(chunk)
    else:
        out = enc.encrypt(data)

    return out

def solve_security_cmd(cmd_buffer: bytes) -> bytes:
    cmd_str = base64.b64encode(cmd_buffer).decode()
    response = mhycrypto.solveSecCmd(cmd_str)

    if response != "":
        return base64.b64decode(response)
    else:
        return b''

def generate_sc_data(server_sc_data: bytes, messages: list[str]):
    sc_str = base64.b64encode(server_sc_data).decode()
    client_sc_data = mhycrypto.genScData(sc_str, messages)

    if client_sc_data != "":
        return base64.b64decode(client_sc_data)
    else:
        return b''