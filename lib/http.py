import datetime
import time
import urllib2

def request_until_succeed(url):
  req = urllib2.Request(url)
  success = False

  while success is False:
    try:
      response = urllib2.urlopen(req)
      if response.getcode() == 200:
          success = True

    except Exception, e:
      print e
      time.sleep(5)

      print "Error for URL %s: %s" % (url, datetime.datetime.now())
      print "Retrying."

  return response.read()
