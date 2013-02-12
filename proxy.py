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

		self.socket.listen(10000)

		while True:
			conn, addr = self.socket.accept()
					
			print "Connection from", addr[0] + ":" +  str(addr[1])	
			start_new_thread(self.handle, (conn,))

	def handle(self, conn):

		data = conn.recv(4096)	

		#TODO(scottbpc): Check for HTTPS traffic and reject it

		(method, headers, payload, hostname) = self.parse_http(data)

		if hostname in self.banned_hosts:
			conn.send(self.banned_html + "\r\n")
			conn.close()
			return	
	
		# TODO(scottbpc): Check payload for banned phrases

		(host, port) = self.parse_host(hostname)

		if host is None:
			print "Host Error: error parsing", hostname

		# TODO(scottbpc): Add cache lookup
		if host == self.hostname and port == self.port:
			self.handle_admin(method, conn, payload, headers)
			return

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

		data = ""

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

		# TODO(scottbpc): Fix this shit
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

		print data	
		print "=================="
		print "METHOD", method
		print "HEADERS", headers
		print "PAYLOAD", payload
		print "=================="

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

	def handle_admin(self, method, conn, payload, headers):
		html = '''<html>
				<head><title>Admin Page</title></head>
				<body><h1>Admin Panel</h1>
					<h2>Add Bans</h2>
					<form name="input" action="add_host" method="post">
						Host: <input type="text" name="host"><input type="submit" value="Submit">
					</form>
					<form name="input" action="add_keyword" method="post">
						Keyword: <input type="text" name="keyword">
					<input type="submit" value="Submit">
					</form>
					<h2>Remove Bans</h2>
					<form name="input" action="del_host" method="post">
						Host: <input type="text" name="host"><input type="submit" value="Submit">
					</form>
					<form name="input" action="del_keyword" method="post">
						Keyword: <input type="text" name="keyword">
					<input type="submit" value="Submit">
					</form>'''
		

		if "POST /add_host" in method:
			tmp = payload.split("host=")[1]
			print "Adding site to banned hosts - ", tmp
			if tmp in self.banned_hosts:
				html = html + "<p>Host '" + tmp + "' already present in ban list</p>"
			else:
				html = html + "<p>Added banned host: '" + tmp + "'</p>"
				self.banned_hosts.append(tmp)

		if "POST /del_host" in method:
			tmp = method.split("del_host?host=")
			tmp = tmp[1].split(" ")[0]
			if tmp in self.banned_hosts:
				print "Removed site from banned hosts -", tmp
				html = html + "<p>Removed banned host " + tmp + "</p>"
				self.banned_hosts.remove(tmp)
			else:
				print "Tried to remove site from banned hosts, not present in ban list -", tmp
				html = html + "<p>Ban list did not previously contain host '" + tmp + "'</p>"

		if "POST /add_keyword" in method:
			tmp = method.split("add_keyword?keyword=")
			tmp = tmp[1].split(" ")[0]
			print "Adding word to banned keywords list - ", tmp
			if tmp in self.bad_keywords:
				html = html + "<p>Keyword '" + tmp + "' already present in bad word list</p>"
			else:
				html = html + "<p>Added banned host: '" + tmp + "'</p>"
				self.bad_keywords.append(tmp)

		if "POST /del_keyword" in method:
			tmp = method.split("del_keyword?keyword=")
			tmp = tmp[1].split(" ")[0]
			if tmp in self.bad_keywords:
				print "Removed site from bad keywords -", tmp
				html = html + "<p>Removed bad keyword '" + tmp + "'</p>"
				self.bad_keywords.remove(tmp)
			else:
				print "Tried to remove keyword from ban list but was not present -", tmp
				html = html + "<p>Ban list did not previously contain keyword '" + tmp + "'</p>"

		html = html + '''<h3>Banned hosts</h3><ul>'''
		for name in self.banned_hosts:
			html = html + "<li>" + name + "</li>"

		html = html + "</ul><h3>Banned keywords</h3><ul>"

		for name in self.bad_keywords:
			html = html + "<li>" + name + "</li>"

		html = html + "</ul>"

		html = html + "<h3>Cached pages:</h3><ul>"
	
		html = html + "<li>None</li>"

		html = html + "</ul></body></html>" + "\r\n"

		conn.send(html)
		conn.close()
		return

if __name__ == "__main__":
	p = Proxy(port=8090)

