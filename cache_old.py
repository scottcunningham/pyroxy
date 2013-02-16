class Cache:

	def __init__(self, max_size):
		self.max_size = max_size
		self.contents = []

	def lookup(self, url):
		for item in self.contents:
			if item[0] == url:
				return item[1]
		return None
	
	def add(self, url, payload):

		for item in self.contents:
			if item[0] == url:
				self.contents.remove(item)
				break

		if len(self.contents) == self.max_size:
			# TODO(scottbpc): Oh god remove this bad hack :(
			self.contents.remove(self.contents[0])
				
		self.contents.append((url, payload))
