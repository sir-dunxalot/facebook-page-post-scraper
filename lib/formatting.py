import inflection
import locale

from urlparse import urlparse

locale.setlocale(locale.LC_ALL, 'en_US')

def humanizeNumber(number):
  return locale.format('%d', number, grouping = True)

def dasherize(string):
  return inflection.parameterize(unicode(string))

def durationToSeconds(duration):

  if isinstance(duration, float):
    return 0

  split_duration = duration.split(':')

  if len(split_duration) > 2:
    h, m, s = split_duration
  else:
    m, s = split_duration
    h = 0

  total_seconds = int(h) * 3600 + int(m) * 60 + int(s)

  return total_seconds

def getDomainName(url):
  if type(url) is not str:
    return ''

  parsed_url = urlparse(url)

  return parsed_url.netloc
