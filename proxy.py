import socket
import gzip
import StringIO
import cache
import re
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
		self.connect_error_html = open("resources/connect.html").read()
	
		print "Starting up. Good luck."

		self.cache.add("hello.de", "<html><h1>aaa</h1></html>")

		self.loop_forever()

	def loop_forever(self):

		# Here, we listen on the assigned port and address, and accept connections
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
		self.socket.bind((self.hostname, self.port))

		self.socket.listen(10000)

		while True:
			# Accept connections, and dispatch a new thread to deal with them
			conn, addr = self.socket.accept()
					
			# print "Connection from", addr[0] + ":" +  str(addr[1])	
			start_new_thread(self.handle, (conn, addr))

	def handle(self, conn, addr):

		# Recieve the request from the browser
		data = conn.recv(8192)	

		# Parse the method, headers, payload and hostname from the HTTP req. - this is explained
		# more thoroughly in the function itself
		(method, headers, payload, hostname) = self.parse_http(data)

		# To thwart any attempted HTTPs traffic (chrome does this a _lot_ without asking)
		if "https://" in method or "CONNECT" in method:
			conn.send("<html><h1>Tunnelling unsupported!</h1></html>")
			conn.close()
			return

		'''
		The problem with Accept-Encoding:
		If the payload is gzipped, then searching for keywords would be fine: we could just
		gunzip the payload. 
		However, there are N ways of encoding the payload of the data, and writing code to decompress
		each of these would be too heavy. 
		So, instead of doing this, I just modify the headers of the HTTP request to ask for uncmopressed
		data.
		'''
		found = False

		for line in headers:
			if "Accept-Encoding" in line:
				line = "Accept-Encoding: "
				found = True
				break

		# Reconstruct the request with the modified Accept-Encoding header
		data = method + "\r\n"
		
		if not found:
			data += "Accept-Encoding: \r\n"
		
		for line in headers:
			data += line + "\r\n"

		data += "\r\n"
		data += payload

		# If the hostname the user is trying to reach is banned, we simply return the "site banned"
		# html to the user's browser 
		if hostname in self.banned_hosts:
			print "[IP", addr[0], "trying to access banned host", hostname, "- blocked]"
			conn.send(self.banned_html + "\r\n")
			conn.close()
			return	

		url = self.parse_url(method, hostname)

		# If we are using a downstream proxy (eg www-proxy.scss.tcd.ie:8000 or proxyc.tcd.ie:8080)
		# we send the request to the proxy, which will pass it on
		if self.downstream_proxy is not "":
			hostname = self.downstream_proxy

		# Parse the hostname and port to connect to
		(host, port) = self.parse_host(hostname)

		if host is None:
			conn.send("<html><h1>Host Error: Could not parse " + hostname + " (note: HTTPS is not supported)</h1></html>\r\n")
			conn.close()
			return

		# If the user navigates to the host and port we are listening on, they will get the webUI -
		# the handle_admin function deals with this
		if host == self.hostname and port == self.port:
			self.handle_admin(method, conn, payload, headers)
			return

		# Look for this address in the cache
		response = self.cache.lookup(url)
		
		# If it is cached, send cached item to the user
		if response is not None and response is not "":
			conn.send(response + "\r\n")
			conn.close()
			return

		# Otherwise, retrieve the response from the remote web server
		outgoing = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		outgoing.settimeout(1)

		try:
			outgoing.connect((host, port))
		except:
			conn.send(self.connect_error_html + "\r\n")	
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

		response_payload = ""
		tmp = response.split("\r\n")[-1:]
		for x in tmp:
			response_payload += x

		''' #Removed because the request header is changed to not allow gzip
		response_headers = response.split("\r\n")[1:][:-2]
	
		gzipped = False

		# Check the response to see whether the payload is gzipped
		for line in response_headers:
			if "Content Encoding" in response and "gzip" in response:
				gzipped = True

		# Gunzip it if we need to
		if gzipped:
			response_payload = gzip.GzipFile(fileobj=StringIO(response_payload)).read()
		'''

		# And search for bad keywords
		for keyword in self.bad_keywords:
			if keyword in response_payload:
				print "[IP", addr[0], " accessing page with banned keyword [", keyword, "]"

		conn.send(response)
		conn.send("\r\n")
		conn.close()

		self.cache.add(url, response_payload)
		return		

	def parse_http(self, data):
		# Split in to an array by HTTP EOL - \r\n
		lines = data.split("\r\n")
		
		# First line will be something like GET http://foo.bar/favicon.ico HTTP/1.0
		method = lines[0]
		# The headers are lines 1 - len-2
		headers = lines[1:][:-2]
		hostname = ""
		payload = lines[-1:][0]

		# Parse out the hostname from the Host header
		for line in headers:
			if line.split(":")[0] == "Host":
				hostname = line.split("Host: ")[1]
	
		return (method, headers, payload, hostname)

	def parse_host(self, host):
		tmp = host.split(":")
		
		if len(tmp) > 2:
			# Then of form http://localhost:111:222, so invalid
			return None

		# Then of form http://hostname:portname, so parse out port
		# Otherwise we assume port 80, the default
		if len(tmp) == 2:
			port = int(tmp[1])

		else:
			port = 80

		return (tmp[0], port)

	def parse_url(self, method, hostname):
		url = ""
		'''
		This extracts the URL to cache
		This is the full URL - sometimes the "method" line will have a relative path, eg:
		GET /favicon.ico HTTP/1.1
		Instead of GET http://foo.bar/favicon.ico HTTP/1.0
		If so, they will be concatenated to get the full URL
		'''
		for request in ["GET", "HEAD", "POST", "PUT", "DELETE", "TRACE", "OPTIONS", "CONNECT", "PATCH"]:
			if re.match(request + " .* " + "HTTP/[01]", method):
				url = method.split(request + " ")[1].split(" HTTP")[0]
		if not "http://" in url:
			url = hostname + url
		return url

	'''
	This method takes a connection to the host/port the proxy is listening on, and serves an "admin" page
	From this page, admins can:
	- Add/remove banned urls
	- Add/remove bad keywords
	- View locally cached pages
	'''
	def handle_admin(self, method, conn, payload, headers):

		# Parse out the URL from the request - /get_cache?url= is the syntax of the links that are provided
		# to view cached pages
		if "/get_cache?url=" in method:
			tmp = method.split("/get_cache?url=")[1].split(" HTTP")[0]
			print "[Fetching cache item for user -", tmp + "]"
			page = self.cache.lookup(tmp)
			if page is None:
				conn.send("<html><h1>Cache error</h1></html>")
				conn.close()
				return
			conn.send(page + "\r\n")
			conn.close()
			return

		# This is the HTML of the admin page
		# There is a lot of it, but it just marks up to forms for adding/removing hosts/keywords, and lists of hosts/keywords/cached pages
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

		'''
		The next 4 sections are similar to above, except for POSTing data from the forms, ie, data being added/removed from the
		lists of keywords and hosts
		'''
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
		
		# Send the lists of banned hosts/bad keywords
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

		# And send the list of cached pages, with links to view them 
		# (which is handled at the start of this function) 
		conn.send(html)
		conn.send("</ul><h3>Cached pages:</h3><ul>")
		
		html = ""

		if len(pages.keys()) == 0:
			html += "<li>(None)</li>"

		pages = self.cache.get_all()
		for url in pages.keys():
			html += "<li> <a href=\"/get_cache?url=" + url + "\">" + url + "</a></li>"

		conn.send(html)
		conn.send("</ul> </body> </html>" + "\r\n")

		conn.close()
		return
	
if __name__ == "__main__":
	p = Proxy(port=8080)

