import cache


c = cache.Cache(4)

c.add("boop.com", "http 10101")
c.add("beep.com", "http 22222")
c.add("omm", "isafdsdfasdfasdf1")
c.add("odsfasdfm", "okok")
c.add("another", "aaa")
c.add("more more", "aaa")
c.add("te", "aaa")




a = c.lookup("boop.com")
a = c.lookup("beep.com")


a = c.lookup("another")
a = c.lookup("odsfasdfm")



print a





