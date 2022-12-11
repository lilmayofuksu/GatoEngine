from itertools import cycle
from typing import Tuple
import os
import base64
import hashlib
import hmac

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
            with open(os.path.join(path, key_path), "r") as f:
                key_id = os.path.basename(key_path)[:1]
                signing_keys[int(key_id)] = RSA.import_key(f.read())
        else:
            with open(os.path.join(path, key_path), "r") as f:
                key_id = os.path.basename(key_path)[:1]
                private_keys[int(key_id)] = RSA.import_key(f.read())

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
    response = mhycrypto.solve_sec_cmd(cmd_buffer)

    if response != b'':
        return response
    else:
        return b''

def generate_sc_data(server_sc_data: bytes, messages: list[str]):
    client_sc_data = mhycrypto.gen_sc_data(server_sc_data, messages)

    if client_sc_data != b'':
        return client_sc_data
    else:
        return b''

def generate_hmac_signature(key, data):
    sig_hash = hmac.new(key.encode('utf8'), data.encode('utf8'), hashlib.sha256).digest()
    return sig_hash.hex()

def gen_version_hash(version, key):
    return base64.b64encode(hashlib.sha1(f"{version}{key}mhy2020".encode("ascii")).digest()).decode()