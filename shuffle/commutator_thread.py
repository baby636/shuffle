import socket
import ssl
import threading
import queue
import time
import select

class Commutator(threading.Thread):
    """
    Class for decoupling of send and recv ops.
    """
    def __init__(self, income, outcome, logger = None, buffsize = 4096, timeout = 0, switch_timeout = 0.1, ssl = False):
        super(Commutator, self).__init__()
        self.income = income
        self.outcome = outcome
        self.logger = logger
        self.alive = threading.Event()
        self.alive.set()
        self.socket = None
        self.frame = '⏎'.encode('utf-8')
        self.MAX_BLOCK_SIZE = buffsize
        self.timeout = timeout
        self.switch_timeout = switch_timeout
        self.ssl = ssl

    def debug(self, obj):
        if self.logger:
            self.logger.put(str(obj))

    def run(self):
        while self.alive.isSet():
            try:
                msg = self.income.get(True, self.switch_timeout)
                self._send(msg)
                self.debug('send!')
            except (queue.Empty, socket.error) as e:
                try:
                    self.socket.setblocking(0)
                    response = self._recv()
                    self.outcome.put_nowait(response)
                    self.debug('recv')
                except (queue.Empty, socket.error) as e:
                    continue

    def join(self, timeout=None):
        self.socket.close()
        self.alive.clear()
        threading.Thread.join(self, timeout)


    def connect(self, host, port):
        try:
            bare_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bare_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # bare_socket.settimeout(self.timeout)
            if self.ssl:
                self.socket = ssl.wrap_socket(bare_socket, ssl_version=ssl.PROTOCOL_TLSv1_2, ciphers="ADH-AES256-SHA")
            else:
                self.socket = bare_socket
            # self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            print(self.socket)
            self.socket.connect((host, port))
            # self.socket.settimeout(self.timeout)
            self.debug('connected')
        except IOError as e:
            self.logger.put(str(e))

    def _send(self, msg):
        print(msg)
        message = msg + self.frame
        self.socket.sendall(message)

    def close(self):
        self.socket.close()
        self.debug('closed')

    def _recv(self):
        response = b''
        while response[-3:] != self.frame:
            response += self.socket.recv(self.MAX_BLOCK_SIZE)
        return response[:-3]

class Channel(queue.Queue):
    """
    simple Queue wrapper for using recv and send
    """
    def __init__(self, switch_timeout = 0.1):
        queue.Queue.__init__(self)
        self.switch_timeout = switch_timeout

    def send(self, message):
        self.put(message,True, self.switch_timeout)
    def recv(self):
        return self.get(True)

class ChannelWithPrint(queue.Queue):

    def send(self, message):
        print(message)
        self.put(message)

    def recv(self):
        return self.get()
