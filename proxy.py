import socket
from thread import *

class Proxy:

	def __init__(self, hostname="localhost", port=8080):
		self.hostname = hostname
		self.port = port 

		# TODO(scottbpc): Set up cache
		
		print "Listening on", hostname + ", port", port

		self.banned_hosts = open("banned_hosts.conf").read().split("\n")
		print "Banned hosts are:", self.banned_hosts

		self.bad_keywords = open("bad_keywords.conf").read().split("\n")
		print "Banned keywords are:", self.bad_keywords

		self.banned_html = open("resources/banned.html").read()

		self.admin_html= open("resources/admin.html").read()

		self.dns_error_html = open("resources/dns.html").read()
	
		print "Starting up. Good luck."

		self.loop_forever()

	def loop_forever(self):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
		self.socket.bind((self.hostname, self.port))

		self.socket.listen(100)

		while True:
			conn, addr = self.socket.accept()
	                
			print "Connection from", addr[0] + ":" +  str(addr[1])	
			start_new_thread(self.handle, (conn,))

	def handle(self, conn):

		data = conn.recv(4096)	

		(method, headers, payload, hostname) = self.parse_http(data)

		#if hostname in self.banned_hosts:
		if False:
			conn.send(self.banned_html + "\r\n")
			conn.close()
			return	
	
		# TODO(scottbpc): Check payload for banned phrases

		(host, port) = self.parse_host(hostname)

		# TODO(scottbpc): Add cache lookup
	
		if host == self.hostname and port == self.port:
			conn.send(self.admin_html + "\r\n")
			conn.close()
			return()

		# lag is somewhere before here

		outgoing = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		outgoing.settimeout(10)

		try:
			outgoing.connect((host, port))
		except:
			print "DNS error - could not resolve host", host
			print "Full hostname was", hostname
			conn.send(self.dns_error_html + "\r\n")	
			conn.close
			outgoing.close()
			return

		outgoing.send(data + "\r\n")

		response = []
    		while True:
	 		try:
				data = outgoing.recv(4096)
				conn.send(data)
			except:
				pass		
			if not data: 
				break

		conn.send("\r\n")	
		conn.close()

	def parse_http(self, data):
		lines = data.split("\r\n")
		method = lines[0]

		header = True
		headers = []
		payload = ""
		hostname = ""

		tmp = []

		for line in lines:
			if header:
				headers.append(line)
				if line.split(":")[0] == "Host":
					hostname = line.split("Host: ")[1]
			elif line == "\r\n":
				header = False

			else:
				tmp.append(line)

		payload = ''.join(tmp)

		return (method, headers, payload, hostname)

	def parse_host(self, host):
		tmp = host.split(":")
		
		if len(tmp) > 2:
			# Then of form localhost:111:222
			return None

		if len(tmp) == 2:
			port = int(tmp[1])

		else:
			port = 80

		return (tmp[0], port)


if __name__ == "__main__":
	p = Proxy(port=8080)
	
