from OpenSSL import SSL
from socketserver import ForkingTCPServer
import socket

class TLSException(Exception): pass

class MissingKeyException(TLSException):
	def __init__(self):
		super().__init__("Must supply keyfile and certfile to TLSServer constructor.")

class TLSServer(ForkingTCPServer):
	def __init__(self,server_address,RequestHandlerClass,keyfile=None,certfile=None,bind_and_activate=True):
		if keyfile is None or certfile is None:
			raise MissingKeyException()
		ForkingTCPServer.__init__(self,server_address,RequestHandlerClass)
		self._ctx = SSL.Context(SSL.TLS_SERVER_METHOD)
		# don't allow anything worse than TLS v1.2 (this is broken so I've commented it out for the time being)
#		self._ctx.set_min_proto_version(SSL.TLSv1_2_METHOD)
		self._ctx.use_privatekey_file(keyfile)
		self._ctx.use_certificate_file(certfile)
		self._ctx.set_verify(SSL.VERIFY_PEER,self._verify_cb)
		self.socket = SSL.Connection(self._ctx,socket.socket(self.address_family,self.socket_type))
		if bind_and_activate:
			self.server_bind()
			self.server_activate()
	def _verify_cb(self,conn,x509,errno,depth,ok):
		conn.was_ok = ok
		return True # accept any peer cert
	def shutdown_request(self,request):
		try:
			request.shutdown() # send close_notify
		except SSL.Error: # might cause an issue here
			pass
		except OSError: # might get ENOCONN
			pass
		self.close_request(request)
