import socket
import gzip
import StringIO
import cache
from thread import *

class Proxy:

	# The proxy will by default listen on localhost:8080, no downstream proxy, with 64 cached items
	def __init__(self, hostname="localhost", port=8080, downstream_proxy="", max_cache = 64):

		self.hostname = hostname
		self.port = port 
		self.downstream_proxy = downstream_proxy

		self.cache = cache.Cache(max_cache)

		print "Listening on", hostname + ", port", port

		# Banned hosts and bad keywords are loaded from text files in the current directory,
		# separated by newlines. The [:-1] simply removes the last item, which will be empty
		self.banned_hosts = open("banned_hosts.conf").read().split("\n")[:-1]
		print "Banned hosts are:", self.banned_hosts

		self.bad_keywords = open("bad_keywords.conf").read().split("\n")[:-1]
		print "Banned keywords are:", self.bad_keywords

		# Custom HTML pages are loaded from the resources/ directory.
		# These are used for responses to various bad queries.
		self.banned_html = open("resources/banned.html").read()
		self.dns_error_html = open("resources/dns.html").read()
	
		print "Starting up. Good luck."

		self.loop_forever()

	def loop_forever(self):

		# Here, we listen on the assigned port and address, and accept connections
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
		self.socket.bind((self.hostname, self.port))

		self.socket.listen(10000)

		while True:
			# Accept connections, and dispatch a new thread to deal with them
			conn, addr = self.socket.accept()
					
			print "Connection from", addr[0] + ":" +  str(addr[1])	
			start_new_thread(self.handle, (conn, addr))

	def handle(self, conn, addr):

		# Recieve the request from the browser
		data = conn.recv(8192)	

		# Parse the method, headers, payload and hostname from the HTTP req. - this is explained
		# more thoroughly in the function itself
		(method, headers, payload, hostname) = self.parse_http(data)

		# If the hostname the user is trying to reach is banned, we simply return the "site banned"
		# html to the user's browser 
		if hostname in self.banned_hosts:
			print "[IP", addr[0], "trying to access banned host", hostname, "- blocked]"
			conn.send(self.banned_html + "\r\n")
			conn.close()
			return	
	
		# If we are using a downstream proxy (eg www-proxy.scss.tcd.ie:8000 or proxyc.tcd.ie:8080)
		# we send the request to the proxy, which will pass it on
		if self.downstream_proxy is not "":
			hostname = self.downstream_proxy

		# Parse the hostname and port to connect to
		(host, port) = self.parse_host(hostname)

		if host is None:
			print "[Host Error: error parsing", hostname, "]"
			conn.send("<html><h1>Host Error: Could not parse " + hostname + " (note: HTTPS is not supported)</h1></html>")
			conn.close()
			return

		# If the user navigates to the host and port we are listening on, they will get the webUI -
		# the handle_admin function deals with this
		if host == self.hostname and port == self.port:
			print "[IP", addr[0], "accessing admin panel]"
			self.handle_admin(method, conn, payload, headers)
			return

		# Look for this address in the cache
		response = self.cache.lookup(hostname)
		
		# If it is cached, send it to the user
		if response is not None:
			conn.send(tmp + "\r\n")
			conn.close()
			return

		# Otherwise, retrieve te response
		outgoing = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		outgoing.settimeout(1)

		try:
			outgoing.connect((host, port))
		except:
			print "Error - could not resolve host \"", host, "\" (may be garbled HTTPS header)"
			print "Full hostname was", hostname
			conn.send(self.dns_error_html + "\r\n")	
			conn.close
			outgoing.close()
			return

		# Send the original request outbound
		outgoing.send(data + "\r\n")

		response = ""

		while True:
	 		try:
				response += outgoing.recv(1024)
				if not response:
					break
			except:
				break	
			if not data: 
				break

		# Check the response to see whether the payload is gzipped
		if "Content Encoding" in response and "gzip" in response:
			gzipped = True
		else:
			gzipped = False

		print "!!!!!!!", response, "!!!!!!"

		# Gunzip it if we need to
		if gzipped:
			response = gzip.GzipFile(fileobj=StringIO(response)).read()

		# And search for bad keywords
		for keyword in self.bad_keywords:
			if keyword in response:
				print "[IP", addr[0], " accessing page with banned keyword [", keyword, "]"

		conn.send(response)
		conn.send("\r\n")
		conn.close()
	
		self.cache.add(hostname, data)
		return		

	def parse_http(self, data):
		lines = data.split("\r\n")
		method = lines[0]

		header = True
		headers = []
		payload = ""
		hostname = ""

		for line in lines:
			if header:
				headers.append(line)
				if line.split(":")[0] == "Host":
					hostname = line.split("Host: ")[1]
			elif line == '':
				break

		payload = lines[-1:][0]

		return (method, headers, payload, hostname)

	def parse_url(self, method, hostname):
		tmp = method.split("GET ")[1].split(" HTTP")[0]
		if tmp == "/":
			return hostname
		if hostname[-1:] == "/":
			return hostname[:-1] + tmp

		return hostname + tmp

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

		if "GET /get_cache?url=" in method:
			tmp = method.split("/get_cache?url=")[1].split(" HTTP")[0]
			print "[Fetching cache item for user - ", tmp + "]"
			page = self.cache.lookup(tmp)
			print "CACHED ITEM WAS " + page
			conn.send(page + "\r\n")
			conn.close()
			return

		conn.send('''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">''')
		conn.send('''<html xmlns="http://www.w3.org/1999/xhtml">''')
		conn.send('''<head><title>Admin Panel</title></head>''')
		conn.send('''<body><h1>Admin Panel</h1><h2>Add Bans</h2>''')
		conn.send('''<form action="add_host" method="post">''')
		conn.send('''<p>Host: <input type="text" name="host"/></p></form>''')
		conn.send('''<form action="add_keyword" method="post"><p>Keyword: <input type="text" name="keyword"/></p></form>''')
		conn.send('''<h2>Remove Bans</h2>''')
		conn.send('''<form action="del_host" method="post">''')
		conn.send('''<p>Host: <input type="text" name="host"/></p></form>''')
		conn.send('''<form action="del_keyword" method="post">''')
		conn.send('''<p>Keyword: <input type="text" name="keyword"/></p></form>''')

		html = ""

		if "POST /add_host" in method:
			tmp = payload.split("host=")[1]
			print "Adding site to banned hosts - ", tmp
			if tmp in self.banned_hosts:
				html += " <p>Host '" + tmp + "' already present in ban list</p>"
			else:
				html += " <p>Added banned host: '" + tmp + "'</p>"
				self.banned_hosts.append(tmp)

		conn.send(html)
		html = ""

		if "POST /del_host" in method:
			tmp = payload.split("host=")[1]
			if tmp in self.banned_hosts:
				print "Removed site from banned hosts -", tmp
				html += " <p>Removed banned host " + tmp + "</p>"
				self.banned_hosts.remove(tmp)
			else:
				print "Tried to remove site from banned hosts, not present in ban list -", tmp
				html += "<p> Banned hosts list did not previously contain host '" + tmp + "'</p>"

		conn.send(html)
		html = ""		

		if "POST /add_keyword" in method:
			tmp = payload.split("keyword=")[1]
			print "Adding word to banned keywords list - ", tmp
			if tmp in self.bad_keywords:
				html += " <p>Keyword '" + tmp + "' already present in bad word list</p>"
			else:
				html += " <p>Added banned keyword: '" + tmp + "'</p>"
				self.bad_keywords.append(tmp)
		conn.send(html)
		html = ""

		if "POST /del_keyword" in method:
			tmp = payload.split("keyword=")[1]
			if tmp in self.bad_keywords:
				print "Removed site from bad keywords -", tmp
				html += "<p> Removed bad keyword '" + tmp + "'</p>"
				self.bad_keywords.remove(tmp)
			else:
				print "Tried to remove keyword from ban list but was not present -", tmp
				html += "<p> Ban list did not previously contain keyword '" + tmp + "'</p>"

		conn.send(html)
		conn.send("<h3>Banned hosts</h3><ul>")
		html = ""
		
		if len(self.banned_hosts) == 0:
			html += " <p>(None) </p>"

		else:
			for name in self.banned_hosts:
				html += " <li>\"" + name + "\"</li>"

		conn.send(html)
		conn.send(" </ul><h3>Banned keywords</h3><ul>")
		html = ""

		if len(self.bad_keywords) == 0:
			html += " <li>(None)</li>"

		for name in self.bad_keywords:
			html += " <li>\"" + name + "\"</li>"

		conn.send(html)
		conn.send("</ul><h3>Cached pages:</h3><ul>")
		
		html = ""

		pages = self.cache.get_all()
		for url in pages.keys():
			html += "<li> <a href=\"/get_cache?url=" + url + "\">" + url + "</a></li>"

		conn.send(html)
		conn.send("</ul> </body> </html>\r\n")

		conn.close()
		return

if __name__ == "__main__":
	p = Proxy(port=8090)

