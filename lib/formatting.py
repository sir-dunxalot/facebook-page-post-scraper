import inflection
import locale

locale.setlocale(locale.LC_ALL, 'en_US')

def humanizeNumber(number):
  return locale.format('%d', number, grouping = True)

def dasherize(string):
  return inflection.parameterize(unicode(string))
