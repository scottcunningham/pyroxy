from Queue import deque

class Cache:

	def __init__(self, max_size):
		self.max_size = max_size
		self.urls = deque()
		self.contents = {}

	def lookup(self, url):
		if url in self.urls:
			# Move url to front of queue
			self.urls.remove(url)
			self.urls.append(url)
			# Return the payload
			return self.contents[url]
		return None
	
	def add(self, url, payload):

		print "Adding", url, "to cache"

		if url in self.urls:
			print "[Item", url, "already present in cache]"
			# Remove item from queue to add it to front later
			self.urls.remove(url)
			self.urls.append(url)
			return self.contents[url]

		else:
			if len(self.urls) == self.max_size:
				# Remove oldest item from queue
				tmp = self.urls.popleft()
				# Remove this item from cache
				del self.urls[tmp]
				print "Removed URL", tmp, "from cache"
			# Add item to cache
			self.urls.append(url)
			self.contents[url] = payload
