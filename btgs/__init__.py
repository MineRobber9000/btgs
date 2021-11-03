from btgs.tls import TLSServer
from btgs.server import GeminiRequestHandler

def serve_static(host,keyfile,certfile,port=1965,hostnames=[],root="/var/gemini"):
	requesthandlerclass = type("requesthandlerclass",(GeminiRequestHandler,),dict(PORT=port,ROOT=root,HOSTS=hostnames))
	return serve(requesthandlerclass,host,keyfile,certfile,port)

def serve(rhc,host,keyfile,certfile,port=1965):
	server = TLSServer((host,port),rhc,keyfile,certfile,bind_and_activate=False)
	server.allow_reuse_address=True
	server.server_bind()
	server.server_activate()
	server.serve_forever()
