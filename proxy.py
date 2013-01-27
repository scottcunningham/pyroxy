import socket
import thread

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
	
		print "Starting up. Good luck."

		self.loop_forever()

	def loop_forever(self):
		self.socket = socket.socket()
	
		self.socket.bind((self.hostname, self.port))

		# TODO(scottbpc): Re-do socket listening etc

		while True:
			self.socket.listen(1)

			# TODO(scottbpc): Thread this well
			conn, addr = self.socket.accept()
	                
			tmp = []
        	        
			data = conn.recv(8192)
			
			self.handle(conn, data)

	def handle(self, conn, data):

		(method, headers, payload, hostname) = self.parse_http(data)

		#if hostname in self.banned_hosts:
		if False:
			print "Sending crap!"
			# TODO(scottbpc): Reply with HTML file
			conn.send(self.banned_html + "\r\n")
			conn.close()
			return	
	
		# TODO(scottbpc): Check payload for banned phrases

		print "Parsing"

		(host, port) = self.parse_host(hostname)

		# TODO(scottbpc): Add cache lookup
	
		if host == self.hostname and port == self.port:
			print "Hooray!"
			conn.send(self.admin_html + "\r\n")
			conn.close()
			return()

		print "Going to", host, port
	
		outgoing = socket.socket()
		outgoing.connect((host, port))
	
		print "Sending on deh data"	
		outgoing.send(data + "\r\n")

		print "Gettin da shi"
		response = []
    		while True:
        		data = outgoing.recv(8192)
        		if not data: break
        		print "mo shi"
			response.append(data)
    		response = ''.join(response)
		
		print response

		conn.send(response + "\r\n")

	def parse_http(self, data):
		lines = data.split("\r\n")
	
		print data
	
		method = lines[0]

		header = True
		headers = []
		payload = ""
		hostname = ""

		for line in lines:
			if header:
				headers.append(line)
				if line.split(":")[0] == "Host":
					print "Host line is", line
					hostname = line.split("Host: ")[1]
			elif line == "\r\n":
				header = False

			else:
				payload.join(line)

		return (method, headers, payload, hostname)

	def parse_host(self, host):
		tmp = host.split(":")
		print tmp
		
		if len(tmp) > 2:
			# Then of form localhost:111:222
			return None

		if len(tmp) == 2:
			port = int(tmp[1])

		else:
			port = 80

		return (tmp[0], port)


if __name__ == "__main__":
	p = Proxy(port=8000)
	
