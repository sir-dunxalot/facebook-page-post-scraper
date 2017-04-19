import json
import datetime
import csv
import argparse
import os
import sys
import time

from fixtures import pages_to_parse
from pync import Notifier
from lib import cli, http

# Start of options

app_id = '1448270435248078'
app_secret = '02cc640f23fbe7824b8aa8678178c56e' # DO NOT SHARE WITH ANYONE!
get_reaction_stats = False;
output_dir = 'data/scraped'

# End of options

date_format = "%d-%m-%Y"
pages = pages_to_parse.pages

# Parse arguments given via the CLI

def valid_date(s):
  try:
    return datetime.datetime.strptime(s, date_format)
  except ValueError:
    msg = "Not a valid date: %s." % s

    raise argparse.ArgumentTypeError(msg)

parser = argparse.ArgumentParser(description = 'Options for pulling data from FB')

parser.add_argument('--date_since', type = valid_date, help = 'Start date of the date range for which you want to pull data')
parser.add_argument('--date_until', type = valid_date, help = 'End date of the date range for which you want to pull data')

args = parser.parse_args()

# Set date defaults is none are passed

date_now = datetime.datetime.now()

date_since = date_now - datetime.timedelta(days = 2 * 365) if args.date_since is None else \
  args.date_since

if date_since > date_now: # Make sure date_since is not in the future
  raise argparse.ArgumentTypeError('date_since cannot be in the future')

date_until = date_now if args.date_until is None else \
  args.date_until

if date_since > date_until:
  raise argparse.ArgumentTypeError('date_since cannot be after date_until')

# Create access token

access_token = app_id + "|" + app_secret

# Needed to write tricky unicode correctly to csv

def unicode_normalize(text):
  return text.translate({ 0x2018:0x27, 0x2019:0x27, 0x201C:0x22, 0x201D:0x22,
                            0xa0:0x20 }).encode('utf-8')

def getFacebookPageFeedData(page_id, access_token, num_statuses):

  # Construct the URL string; see http://stackoverflow.com/a/37239851 for
  # Reactions parameters
  base = 'https://graph.facebook.com/v2.6'
  node = '/%s/posts' % page_id
  fields = "/?fields=message,link,created_time,type,name,id,properties," + \
          "comments.limit(0).summary(true),shares,reactions" + \
          ".limit(0).summary(true)"
  parameters = "&limit=%s&access_token=%s" % (num_statuses, access_token)
  url = base + node + fields + parameters

  # If a date range is provided, use it

  if date_since is not None:
    timestamp_since = time.mktime(date_since.timetuple())
    url = url + '&since=%s' % timestamp_since

  if date_until is not None:
    timestamp_until = time.mktime(date_until.timetuple())
    url = url + '&until=%s' % timestamp_until

  # retrieve data
  data = json.loads(http.request_until_succeed(url))

  return data

def getReactionsForStatus(status_id, access_token):

  # See http://stackoverflow.com/a/37239851 for Reactions parameters
      # Reactions are only accessable at a single-post endpoint

  base = 'https://graph.facebook.com/v2.6'
  node = "/%s" % status_id
  reactions = "/?fields=" \
          "reactions.type(LIKE).limit(0).summary(total_count).as(like)" \
          ",reactions.type(LOVE).limit(0).summary(total_count).as(love)" \
          ",reactions.type(WOW).limit(0).summary(total_count).as(wow)" \
          ",reactions.type(HAHA).limit(0).summary(total_count).as(haha)" \
          ",reactions.type(SAD).limit(0).summary(total_count).as(sad)" \
          ",reactions.type(ANGRY).limit(0).summary(total_count).as(angry)"
  parameters = "&access_token=%s" % access_token
  url = base + node + reactions + parameters

  # retrieve data
  data = json.loads(http.request_until_succeed(url))

  return data


def processFacebookPageFeedStatus(status, access_token):

  # The status is now a Python dictionary, so for top-level items,
  # we can simply call the key.

  # Additionally, some items may not always exist,
  # so must check for existence first

  status_id = status['id']
  status_message = '' if 'message' not in status.keys() else \
          unicode_normalize(status['message'])
  link_name = '' if 'name' not in status.keys() else \
          unicode_normalize(status['name'])
  status_type = status['type']
  status_link = '' if 'link' not in status.keys() else \
          unicode_normalize(status['link'])

  # Get length, if available

  status_properties = [] if 'properties' not in status.keys() else \
          status['properties']
  status_length_properties = filter(lambda x: x['name'] == 'Length', status_properties) # Find length
  status_video_length = '' if len(status_length_properties) == 0 else \
          status_length_properties[0]['text']

  # Time needs special care since a) it's in UTC and
  # b) it's not easy to use in statistical programs.

  status_published = datetime.datetime.strptime(
          status['created_time'],'%Y-%m-%dT%H:%M:%S+0000')
  status_published = status_published + \
          datetime.timedelta(hours=-5) # EST
  status_published = status_published.strftime(
          '%Y-%m-%d %H:%M:%S') # best time format for spreadsheet programs

  # Nested items require chaining dictionary keys.

  num_reactions = 0 if 'reactions' not in status else \
          status['reactions']['summary']['total_count']
  num_comments = 0 if 'comments' not in status else \
          status['comments']['summary']['total_count']
  num_shares = 0 if 'shares' not in status else status['shares']['count']

  # Counts of each reaction separately; good for sentiment
  # Only check for reactions if past date of implementation:
  # http://newsroom.fb.com/news/2016/02/reactions-now-available-globally/

  reactions = getReactionsForStatus(status_id, access_token) if \
          status_published > '2016-02-24 00:00:00' and get_reaction_stats else {}

  num_likes = 0 if 'like' not in reactions else \
          reactions['like']['summary']['total_count']

  # Special case: Set number of Likes to Number of reactions for pre-reaction
  # statuses

  num_likes = num_reactions if status_published < '2016-02-24 00:00:00' \
          else num_likes

  def get_num_total_reactions(reaction_type, reactions):
    if reaction_type not in reactions:
      return 0
    else:
      return reactions[reaction_type]['summary']['total_count']

  num_loves = get_num_total_reactions('love', reactions)
  num_wows = get_num_total_reactions('wow', reactions)
  num_hahas = get_num_total_reactions('haha', reactions)
  num_sads = get_num_total_reactions('sad', reactions)
  num_angrys = get_num_total_reactions('angry', reactions)

  # Return a tuple of all processed data

  return (status_id, status_message, link_name, status_type, status_link,
          status_published, status_video_length, num_reactions, num_comments, num_shares,
          num_likes, num_loves, num_wows, num_hahas, num_sads, num_angrys)

def scrapeFacebookPageFeedStatus(page, access_token):

  # Check the file doesn't already exist

  page_id = page['page_id']
  page_name = page['name']

  date_since_string = date_since.strftime(date_format)
  date_until_string = date_until.strftime(date_format)

  formatted_page_name = '-'.join(page_name.lower().split())

  csv_file_path = '%s/%s_posts_%s_%s.csv' % (output_dir, formatted_page_name, date_since_string, date_until_string)

  if os.path.isfile(csv_file_path):
    Notifier.notify('File already exists - response needed')
    overwrite_file = cli.ask('The file %s already exists. Do you want to overwrite it?' % csv_file_path)

    if not overwrite_file:

      # End the scraping but don't stop module's execution
      # so we can scrape subsequent pages

      print('Skipping %s' % page_name)

      return

  with open(csv_file_path, 'wb') as file:
    w = csv.writer(file)
    w.writerow(["status_id", "status_message", "link_name", "status_type",
                "status_link", "status_published", "status_video_length", "num_reactions",
                "num_comments", "num_shares", "num_likes", "num_loves",
                "num_wows", "num_hahas", "num_sads", "num_angrys"])

    has_next_page = True
    num_processed = 0   # keep a count on how many we've processed
    scrape_starttime = datetime.datetime.now()

    print "Scraping Page: %s (%s)" % (page_name, page_id)

    statuses = getFacebookPageFeedData(page_id, access_token, 100)

    while has_next_page:
      for status in statuses['data']:

        # Ensure it is a status with the expected metadata
        if 'reactions' in status:
          w.writerow(processFacebookPageFeedStatus(status,
                access_token))

        # output progress occasionally to make sure code is not
        # stalling
        num_processed += 1

        if num_processed % 100 == 0:
          print "%s Statuses Processed: %s" % \
                (num_processed, datetime.datetime.now())

      # if there is no next page, we're done.
      if 'paging' in statuses.keys():
        statuses = json.loads(http.request_until_succeed(
                                  statuses['paging']['next']))
      else:
        has_next_page = False

    file.close()

    print "\nDone!\n%s Statuses Processed in %s\n" % \
            (num_processed, datetime.datetime.now() - scrape_starttime)

    Notifier.notify('Finished scraping %s' % page_name)


if __name__ == '__main__':
  for page in pages:
    scrapeFacebookPageFeedStatus(page, access_token)

  Notifier.notify('Finished scraping all FB data')
