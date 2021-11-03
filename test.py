from btgs.tls import TLSServer
from btgs.server import GeminiRequestHandler

class TestrootGeminiRequestHandler(GeminiRequestHandler):
	ROOT = "testroot"
	PORT = 1966
	HOSTS = ["7f000001.nip.io"]

server = TLSServer(('127.0.0.1',1966),TestrootGeminiRequestHandler,"localhost.key","localhost.crt",False)
server.allow_reuse_address = True
server.server_bind()
server.server_activate()
server.serve_forever()
