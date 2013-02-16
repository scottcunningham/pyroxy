import socket
import gzip
import StringIO
from thread import *

class Proxy:

	def __init__(self, hostname="localhost", port=8080, downstream_proxy=""):
		self.hostname = hostname
		self.port = port 
		self.downstream_proxy = downstream_proxy

		# TODO(scottbpc): Set up cache
		
		print "Listening on", hostname + ", port", port

		self.banned_hosts = open("banned_hosts.conf").read().split("\n")[:-1]
		print "Banned hosts are:", self.banned_hosts

		self.bad_keywords = open("bad_keywords.conf").read().split("\n")[:-1]
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
			start_new_thread(self.handle, (conn, addr))

	def handle(self, conn, addr):

		data = conn.recv(8192)	

		(method, headers, payload, hostname, gzipped) = self.parse_http(data)

		if self.downstream_proxy is not "":
			hostname = self.downstream_proxy

		if hostname in self.banned_hosts:
			print "[IP", addr[0], "trying to access banned host", hostname, "- blocked]"
			conn.send(self.banned_html + "\r\n")
			conn.close()
			return	
	
		if gzipped:
			payload = gzip.GzipFile(fileobj=StringIO(payload)).read()

		# TODO(scottbpc): Test keyword lookup once payload is extracted properly
		for keyword in self.bad_keywords:
			if keyword in payload:
				print "[IP", addr[0], " accessing page with banned keyword [", keyword, "]"

		(host, port) = self.parse_host(hostname)

		if host is None:
			print "[Host Error: error parsing", hostname, "]"
			conn.send("<html><h1>Host Error: Could not parse " + hostname + " (note: HTTPS is not supported)</h1></html>")
			conn.close()
			return

		# TODO(scottbpc): Add cache lookup
		if host == self.hostname and port == self.port:
			print "[IP", addr[0], "accessing admin panel]"
			self.handle_admin(method, conn, payload, headers)
			return

		outgoing = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		outgoing.settimeout(1)

		try:
			print "~connecting outbound to", host, port
			outgoing.connect((host, port))
		except:
			print "DNS error - could not resolve host", host, " - may be garbled HTTPS header"
			print "Full hostname was", hostname
			conn.send(self.dns_error_html + "\r\n")	
			conn.close
			outgoing.close()
			return

		outgoing.send(data + "\r\n")

		data = ""

		while True:
	 		try:
				data += outgoing.recv(1024)
				if not data:
					break
				#conn.send(data)
			except:
				break	
			if not data: 
				break
		conn.send(data)

		conn.send("\r\n")	
		conn.close()

	def parse_http(self, data):
		lines = data.split("\r\n")
		method = lines[0]

		header = True
		headers = []
		payload = ""
		hostname = ""
		gzipped = False

		# TODO(scottbpc): Fix this shit
		for line in lines:
			if header:
				headers.append(line)
				if "Content-Encoding" in line:
					if line.split("Content-Encoding:")[1] == "gzip":
						gzipped = True
				if line.split(":")[0] == "Host":
					hostname = line.split("Host: ")[1]
			elif line == '':
				break

		payload = lines[-1:][0]

		return (method, headers, payload, hostname, gzipped)

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
		html = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
		        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
				<html xmlns="http://www.w3.org/1999/xhtml">
				<head>
					<title>Admin Panel</title>
				</head>
				<body><h1>Admin Panel</h1>
					<h2>Add Bans</h2>
					<form action="add_host" method="post">
						<p>Host: <input type="text" name="host"/></p>
					</form>
					<form action="add_keyword" method="post">
						<p>Keyword: <input type="text" name="keyword"/></p>
					</form>
					<h2>Remove Bans</h2>
					<form action="del_host" method="post">
						<p>Host: <input type="text" name="host"/></p>
					</form>
					<form action="del_keyword" method="post">
						<p>Keyword: <input type="text" name="keyword"/></p>
					</form>'''
		

		if "POST /add_host" in method:
			tmp = payload.split("host=")[1]
			print "Adding site to banned hosts - ", tmp
			if tmp in self.banned_hosts:
				html = html + " <p>Host '" + tmp + "' already present in ban list</p>"
			else:
				html = html + " <p>Added banned host: '" + tmp + "'</p>"
				self.banned_hosts.append(tmp)

		if "POST /del_host" in method:
			tmp = payload.split("host=")[1]
			if tmp in self.banned_hosts:
				print "Removed site from banned hosts -", tmp
				html = html + " <p>Removed banned host " + tmp + "</p>"
				self.banned_hosts.remove(tmp)
			else:
				print "Tried to remove site from banned hosts, not present in ban list -", tmp
				html = html + "<p> Banned hosts list did not previously contain host '" + tmp + "'</p>"

		if "POST /add_keyword" in method:
			tmp = payload.split("keyword=")[1]
			print "Adding word to banned keywords list - ", tmp
			if tmp in self.bad_keywords:
				html = html + " <p>Keyword '" + tmp + "' already present in bad word list</p>"
			else:
				html = html + " <p>Added banned keyword: '" + tmp + "'</p>"
				self.bad_keywords.append(tmp)

		if "POST /del_keyword" in method:
			tmp = payload.split("keyword=")[1]
			if tmp in self.bad_keywords:
				print "Removed site from bad keywords -", tmp
				html = html + "<p> Removed bad keyword '" + tmp + "'</p>"
				self.bad_keywords.remove(tmp)
			else:
				print "Tried to remove keyword from ban list but was not present -", tmp
				html = html + "<p> Ban list did not previously contain keyword '" + tmp + "'</p>"

		html = html + ''' <h3>Banned hosts</h3><ul>'''
		
		if len(self.banned_hosts) == 0:
			html = html + " <p>(None) </p>"

		else:
			for name in self.banned_hosts:
				html = html + " <li>\"" + name + "\"</li>"

		html = html + " </ul><h3>Banned keywords</h3><ul>"

		if len(self.bad_keywords) == 0:
			html = html + " <li>(None)</li>"

		for name in self.bad_keywords:
			html = html + " <li>\"" + name + "\"</li>"

		html = html + " </ul>"
		
		html = html + " <h3>Cached pages:</h3><ul>"
	
		html = html + " <li>(None)</li>"
		html = html + " </ul> </body> </html>"

		conn.send(html + "\r\n")
		conn.close()
		return

if __name__ == "__main__":
	p = Proxy(port=8080)

