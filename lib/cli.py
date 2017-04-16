import sys

def ask(question, default = 'no'):
  valid_responses = {
    "yes": True,
    "y": True,
    "no": False,
    "n": False
  }

  if default is None:
    prompt = '[y/n]'
  elif default == 'yes':
    prompt = '[Y/n]'
  elif default == 'no':
    prompt = '[y/N]'
  else:
    raise ValueError("invalid default answer: '%s'" % default)

  while True:
    sys.stdout.write('%s %s' % (question, prompt))

    user_choice = raw_input().lower()

    if default is not None and user_choice == '':
      return valid_responses[default]
    elif user_choice in valid_responses:
      return valid_responses[user_choice]
    else:
      sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")
