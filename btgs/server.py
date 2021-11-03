from socketserver import BaseRequestHandler
import pathlib
import os
import mimetypes
import urllib.parse as urlparse
urlparse.uses_netloc.append("gemini")
urlparse.uses_relative.append("gemini")

class GeminiRequest:
	"""A Gemini request, with URL and access to the underlying socket."""
	def __init__(self,sock,url,initial_buf=b''):
		self._sock = sock
		self._buffer = initial_buf
		self.url = url
		self.parsed = urlparse.urlparse(url)
	def closest_power_of_two(self,n):
		"""Returns the power of two that is closest to, while being greater than, n."""
		retval = 2
		while retval<n: retval*=2
		return retval
	def recv(self,bufsize,flags=0):
		"""A proxy over self._sock.recv that handles the initial buffer as well as other buffer problems."""
		# time to do some funky shit
		# do we have bufsize in our buffer?
		if bufsize<=len(self._buffer):
			# return that much
			retval, self._buffer = self._buffer[:bufsize], self._buffer[bufsize:]
			return retval
		# if not, then ask for a power of two that's more than what was asked for
		temp = self._sock.recv(self.closest_power_of_two(bufsize),flags)
		self._buffer += temp
		# now do we have bufsize in our buffer?
		if bufsize<=len(self._buffer):
			# return that much
			retval, self._buffer = self._buffer[:bufsize], self._buffer[bufsize:]
			return retval
		else: # if not, just return what we have and go for it
			retval, self._buffer = self._buffer, b''
			return retval
	def send(self,*args,**kwargs):
		"""Plain alias of self._sock.sendall."""
		return self._sock.sendall(*args,**kwargs)
	def __getattr__(self,k):
		"""Attempt to alias unknown attributes to self.parsed."""
		# try and get the attribute off the parsed URL object
		return getattr(self.parsed,k)

class GeminiRequestHandler(BaseRequestHandler):
	HOSTS = [] # hostnames we can serve
	PORT = 1965 # port we serve
	ROOT = "/var/gemini" # root directory from which we serve files
	DEFAULT_DEFAULT_META = { # default for the DEFAULT_META var
		40: "Resource temporarily unavailable",
		41: "Server unavailable",
		42: "Unexpected error in CGI program",
		43: "Unexpected error during handling of proxy request",
		44: 60,
		50: "Permanent failure",
		51: "Not found",
		52: "It's gone, Jim",
		53: "Proxy request refused",
		59: "Bad request",
		60: "Provide a client certificate to continue",
		61: "Not authorized to access this content",
		62: "Invalid certificate provided"
	}
	def setup(self):
		"""Gets us ready to handle the request. Any implementation-specific things should be done in setup_overrideable."""
		self.peer_cert = self.request.get_peer_certificate()
		self.setup_overrideable()
	def handle(self):
		"""Handles request. Parses request line and delegates response handling."""
		buffer = b''
		while b'\n' not in buffer and (temp:=self.request.recv(512)): buffer+=temp
		if buffer[buffer.index(b'\n')-1]!=13: # request line must end with \r\n
			self.header(59) # bad request
			return
		request, buffer = buffer[:buffer.index(b'\n')-1], buffer[buffer.index(b'\n')+1:]
		if len(request)>1024: # maximum URL length is 1024 bytes
			self.header(59) # bad request
			return
		try:
			request = self.massage_request_line(request.decode("utf-8"),buffer)
		except:
			self.header(59) # bad request
			return
		if not self.preflight(request):
			return # preflight will return the appropriate status code
		if hasattr(self,f"handle_{request.scheme}"): # if we have a handler for that status...
			getattr(self,f"handle_{request.scheme}")(request) # ...use it
		else: # if not...
			self.header(53) # treat it as a proxy request and refuse it
	def massage_request_line(self,request_line,buffer):
		"""Massages the request line into a GeminiRequest object."""
		return GeminiRequest(self.request,request_line,buffer) # set up GeminiRequest object
	def header(self,response_code,meta=""):
		"""Sends a response header down the line. Will default to the entry in self.DEFAULT_META if it exists and meta is not provided."""
		if not meta: meta = self.DEFAULT_META.get(response_code,"")
		self.request.sendall(f"{response_code!s} {meta}\r\n".encode("utf-8"))
	def preflight(self,request):
		"""Preflight checks. Is the request for a URL we can serve?"""
		if request.hostname not in self.HOSTS:
			self.header(53) # refuse proxy requests
			return False
		port = request.port or 1965 # default to the default port
		if port != self.PORT:
			self.header(53) # refuse proxy requests
			return False
		return True # otherwise we're good
	def handle_gemini(self,request):
		"""Basic static file server. Default for gemini URLs."""
		path = pathlib.Path(request.path.strip("/"))
		file = pathlib.Path(os.path.normpath(request.path.strip("/")))
		if file.is_absolute() or str(file).startswith(".."):
			self.header(59)
			return
		filesystem = pathlib.Path(self.ROOT)/request.hostname/file
		try:
			if not os.access(filesystem,os.R_OK):
				self.header(51) # not found
				return
		except OSError: # some OS-related error, treat it like it doesn't exist
			self.header(51)
			return
		if filesystem.is_dir():
			if (tmp:=filesystem/pathlib.Path("index.gmi")).exists():
				filesystem = tmp
			else:
				self.directory_list(request,filesystem)
				return
		if not filesystem.exists():
			self.header(51) # not found
			return
		else: # it exists and it's a file
			self.send_file(request,filesystem)
	def directory_list(self,request,dir):
		"""Directory listing. I haven't implemented it yet, so it just returns a 40 error."""
		self.header(40,"Resource unavailable") # NYI
	def send_file(self,request,file):
		"""Send the file at pathlib.Path object file to the request at request."""
		mimetype = self.guess_mimetype(file)
		self.header(20,mimetype)
		with file.open("rb") as f:
			while (data:=f.read(2048)):
				request.send(data)
	def guess_mimetype(self,path):
		"""Use self.mime mimetypes.MimeTypes instance to guess mimetypes. Defaults to application/octet-stream."""
		type, encoding = self.mime.guess_type(path.name)
		if encoding: return f"{type}; charset={encoding}"
		else: return type or "application/octet-stream"
	def setup_overrideable(self):
		"""Setting up self.DEFAULT_META and self.mime. If your mixin requires special setup override this method and call super().setup_overrideable(self)."""
		self.DEFAULT_META = {}
		self.DEFAULT_META.update(self.DEFAULT_DEFAULT_META)
		self.mime = mimetypes.MimeTypes()
		self.mime.add_type("text/gemini",".gmi")
		self.mime.add_type("text/gemini",".gemini")
