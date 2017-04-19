import locale

locale.setlocale(locale.LC_ALL, 'en_US')

def humanizeNumber(number):
  return locale.format('%d', number, grouping = True)
