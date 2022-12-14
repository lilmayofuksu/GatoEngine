from collections import deque
import random
import socket
import threading
import time

from lkcp import KcpObj
from loguru import logger
from gatoengine.network.handshake import Handshake

_Address = tuple[str, int]
_BUFFER_SIZE = 1 << 16

class KcpSocket:
    def __init__(self):
        self._time = time.time()
        self.recv_queue = deque()
        self.recv_queue_semaphore = threading.Semaphore(0)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _get_time(self) -> int:
        return time.time() - self._time

    def _kcp_update(self):
        while self.kcp:
            current_time = int(self._get_time() * 1000)
            self.kcp.update(current_time)

            next_time = self.kcp.check(current_time)
            diff = next_time - current_time

            if diff > 0:
                time.sleep(diff / 1000)
    
    def _kcp_recv(self):
        while self.kcp:
            data = self.sock.recv(_BUFFER_SIZE)
            self.kcp.input(data)

            while x := self.kcp.recv()[1]:
                self.recv_queue.append(x)
                #self.recv_queue_semaphore.release()

    def connect(self, addr: _Address) -> bool:
        self.sock.connect(addr)
        self.addr = addr

        hs1 = Handshake(0xff, 0, 0, 1234567890, 0xffffffff)
        self.sock.send(bytes(hs1))
        logger.debug('[C] handshake sended')

        self.sock.settimeout(10.0)

        try:
            data = self.sock.recv(_BUFFER_SIZE)
        except socket.timeout:
            logger.error("Server didn't reply after 10 seconds, aborting.")
            return False

        self.sock.settimeout(None)

        hs2 = Handshake.parse(data)
        logger.debug('[C] handshake received')

        if (hs2.magic1, hs2.enet, hs2.magic2) != (0x145, 1234567890, 0x14514545):
            self.sock.close()
            return False

        self.kcp = KcpObj(
            hs2.conv, hs2.token,
            lambda _, x: self.sock.send(x),
        )
        self.kcp.setmtu(1200)
        self.kcp.wndsize(1024, 1024)
        self.kcp.nodelay(1, 10, 2, 1)

        threading.Thread(target=self._kcp_update, daemon=True).start()
        threading.Thread(target=self._kcp_recv, daemon=True).start()

        return True

    def close(self):
        if not self.kcp:
            return

        hs = Handshake(0x194, self.kcp.conv, self.kcp.token, 1, 0x19419494)
        self.sock.sendto(bytes(hs), self.addr)
        self.kcp = None

        self.sock.close()

    def send(self, data: bytes):
        self.kcp.send(data)

    def recv(self) -> bytes:
        #self.recv_queue_semaphore.acquire()
        if len(self.recv_queue) > 0:
            return self.recv_queue.popleft()
        else:
            return None