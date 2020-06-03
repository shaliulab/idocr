import pickle
import logging
import logging.handlers
import socketserver
import struct
import urllib.request

import requests


from learnmem.client.utils.mixins import HTTPMixin

class LogRecordStreamHandler(socketserver.StreamRequestHandler, HTTPMixin):
    """Handler for a streaming logging request.

    This basically logs the record using whatever logging policy is
    configured locally.
    """

    def __init__(self, *args, **kwargs):
        self._cache = []
        super().__init__(*args, **kwargs)

    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack('>L', chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = self.unPickle(chunk)
            record = logging.makeLogRecord(obj)

            peer_ip = self.connection.getpeername()[0]
            url = "http://%s:%d/%s" % (peer_ip, 9000, "id")
            resp = self._get_json(url)

            # req = urllib.request.Request(url)
            # file_handle = urllib.request.urlopen(req, timeout=5)
            # message = file_handle.read()
            # resp = json.loads(message)
            machine_id = resp["id"]
            self.handleLogRecord(record, machine_id)


    def unPickle(self, data):
        return pickle.loads(data)

    def handleLogRecord(self, record, machine_id):
        # print(record)
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        # print(record.name)
        # print(machine_id)
        url = "http://%s:%d/device/%s/post_logs" % ("localhost", 80, machine_id)
        print(url)
        # print(record.msg)
        # print(record.msg)

        requests.post(url, data={"logs": record.msg})
        # self._get_json(url, post_data={"logs": record.msg})

        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name



        logger = logging.getLogger(name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        # import ipdb; ipdb.set_trace()
        logger.handle(record)

class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver suitable for testing.
    """

    allow_reuse_address = True

    def __init__(self, host='localhost',
                 port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                 handler=LogRecordStreamHandler):

        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        import select
        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort


def main():
    logging.basicConfig(
        format='%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s')
    tcpserver = LogRecordSocketReceiver()
    print('About to start TCP server...')
    tcpserver.serve_until_stopped()

if __name__ == '__main__':
    main()