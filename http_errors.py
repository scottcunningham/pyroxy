#!/usr/bin/python

http_404_html = '''
<html>
	<head>
		<title>Proxy Server</title>
	</head>
	<body>
		<h1>404 - not found</h1>
	</body>
</html>'''

admin_html = '''
<html>
	<h1>MANAGEMENT CONSOLE YEAH</h1>
</html>'''

banned_html = '''
<html>
	<head>
		<title>PyRoxy</title>
	</head>

	<body>
		<h1>Site Banned</h1>
	</body>
</html>'''

dns_error_html = '''
<html>
	<h1>DNS error</h1>
	<h2>We couldn't resolve that domain. Sorry about that :(</h2>
</html>'''
