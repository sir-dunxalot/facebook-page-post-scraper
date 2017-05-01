from __future__ import division

import argparse
import csv
import datetime
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

from fixtures import pages_to_parse
from lib import cli, formatting

# Options

input_path = 'data/scraped'
output_path = 'data/analyzed'

# End of options

# Parse arguments given via the CLI

parser = argparse.ArgumentParser(description = 'Options for analyzing data from FB')

parser.add_argument('action', help = 'The name of the analysis method to run')
parser.add_argument('--output', action = 'store_true', help = 'When present, analysis will be outputted into a CSV file', default = False)
parser.add_argument('--outliers', action = 'store_true', help = 'When present, outliers will be kept in the data set', default = False)
parser.add_argument('--period', help = 'The resample period to use for grouping data', default = 'M')
parser.add_argument('--chart', help = 'The type of chart you would like to plot')
parser.add_argument('--page', help = 'The name of an individual page you would like to run analysis for')

args = parser.parse_args()

resample_period = args.period
chart = args.chart

def describe(df):
  print cli.horizontalRule()
  print df.describe()
  print cli.horizontalRule()

def writeDataFrameToCsv(df):
  print df

  if args.output:
    write_starttime = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    output_file_path = os.path.join(output_path, '%s_%s.csv' % (args.action, write_starttime))

    df.to_csv(output_file_path)

    print 'Dataframe written to %s' % output_file_path

def renderChart(df):
  if args.chart:
    getattr(df.plot, chart)()
  else:
    df.plot()

  plt.show()

def getMatchingFiles():
  glob_string = '*' if args.page is None else \
    '*%s*' % formatting.dasherize(args.page)

  return glob.glob(input_path + '/%s.csv' % glob_string)

def createDataFrame():

  print 'Creating dataframe'

  compilation_start = datetime.datetime.now()

  # Collate all matching CSVs into a single dataframe

  matching_files = getMatchingFiles()

  df = pd.concat((pd.read_csv(file, index_col = False) for file in matching_files))

  # Remove wierd status types because they're used so little (usually zero)

  df = df[(df.status_type != 'note') & (df.status_type != 'event')]

  # Remove reaction counts because they're slow to collect

  columns_to_remove = ['num_loves', 'num_wows', 'num_hahas', 'num_sads', 'num_angrys']

  df.drop(columns_to_remove, axis = 1, inplace = True)

  # Remove outliers (anything outside 3 SDs from the mean)

  if not args.outliers:
    df = df[np.abs(df.num_shares - df.num_shares.mean()) <= (3 * df.num_shares.std())]

  # Add page_id

  df['page_id'] = df['status_id'].apply(lambda x: x.split('_')[0])

  # Format and list by Datetime

  df['Datetime'] = pd.to_datetime(df['status_published'])

  df.set_index('Datetime', inplace = True)

  # Print the duration it took to create the dataframe for informational purposes

  duration = datetime.datetime.now() - compilation_start

  print 'Dataframe created in %s' % duration

  return df

def groupByType():

  df = createDataFrame()

  describe(df['status_type'])

  status_types = df.groupby('status_type').resample(resample_period).size()

  formatted_status_types = status_types.fillna(0)

  if len(getMatchingFiles()) > 1:
    formatted_status_types = formatted_status_types.transpose()
  else:
    formatted_status_types = formatted_status_types.unstack(level = 0)

  writeDataFrameToCsv(formatted_status_types)
  renderChart(formatted_status_types)

def groupByTypePeriodOverPeriod():

  df = createDataFrame()

  status_types = df.groupby('status_type').resample(resample_period).size()

  formatted_status_types = status_types.fillna(0).transpose()

  for column_name in list(formatted_status_types):
    change_column_name = '%s_change' % column_name

    old_value = formatted_status_types[column_name].shift(-1)
    new_value = formatted_status_types[column_name]

    formatted_status_types[change_column_name] = (old_value / new_value * 100) - 100

    del formatted_status_types[column_name]

  # Remove the first row because the data is thrown off by no previous time period

  formatted_status_types = formatted_status_types.ix[1:]

  writeDataFrameToCsv(formatted_status_types)
  renderChart(formatted_status_types)

def groupByPage():

  df = createDataFrame()

  grouped_pages = df.groupby('page_id').resample(resample_period).size()

  formatted_grouped_pages = grouped_pages.fillna(0).transpose()

  page_mapping = {}

  for page in pages_to_parse.pages:
    page_mapping[page['page_id']] = page['name']

  formatted_grouped_pages.rename(columns = page_mapping, inplace = True)

  writeDataFrameToCsv(formatted_grouped_pages)
  renderChart(formatted_grouped_pages)

def groupByPageAndType():

  df = createDataFrame()

  groups = df.groupby(['page_id', 'status_type']).size()

  formatted_groups = groups.unstack(level = 0).transpose()

  page_mapping = {} # TODO: DO ON ROW

  for page in pages_to_parse.pages:
    page_mapping[page['page_id']] = page['name']

  formatted_groups.rename(index = page_mapping, inplace = True)

  formatted_groups = formatted_groups.apply(lambda row: percentagizeRow(row), axis = 1).fillna(0)

  writeDataFrameToCsv(formatted_groups)
  renderChart(formatted_groups)

def percentagizeRow(row):
  total = row.sum()

  for index, value in enumerate(row):
    row[index] = value / total * 100

  return row

def postLengths():

  df = createDataFrame()

  df['message_length'] = df['status_message'].astype(str).apply(len)

  grouped_lengths = df.resample(resample_period).mean()['message_length']

  writeDataFrameToCsv(grouped_lengths)
  renderChart(grouped_lengths)

def postLengthsGroupByType():

  df = createDataFrame()

  df['message_length'] = df['status_message'].astype(str).apply(len)

  describe(df['message_length'])

  grouped_lengths = df.groupby('status_type').resample(resample_period).mean()['message_length']

  formatted_grouped_lengths = grouped_lengths.unstack(level = 0).fillna(0)

  writeDataFrameToCsv(formatted_grouped_lengths)
  renderChart(formatted_grouped_lengths)

def videoLengths():

  df = createDataFrame()

  # Remove non-video posts

  df = df[df.status_type == 'video']

  df['video_length_seconds'] = df['status_video_length'].apply(lambda x: formatting.durationToSeconds(x))

  describe(df['video_length_seconds'])

  grouped_lengths = df.resample(resample_period).mean()['video_length_seconds']

  writeDataFrameToCsv(grouped_lengths)
  renderChart(grouped_lengths)

def averageEngagementByType():

  df = createDataFrame()

  status_types = df.groupby('status_type').mean()

  describe(status_types)

  formatted_status_types = status_types.fillna(0).transpose()

  writeDataFrameToCsv(formatted_status_types)
  renderChart(formatted_status_types)

def groupByDomainName():

  # TODO: Warn if page not supplied and ask for CLI confirmation

  df = createDataFrame()

  # Get rid of non-links

  df = df[df.status_type == 'link']

  df['link_domain'] = df['status_link'].apply(lambda x: formatting.getDomainName(x))

  grouped_domains = df.groupby('link_domain').resample(resample_period).size()

  writeDataFrameToCsv(grouped_domains)
  renderChart(grouped_domains)

def virality():
  df = createDataFrame()
  output = pd.DataFrame(columns = ['status_type', 'virality'])
  status_types = df.status_type.unique()
  total_shares = df['num_shares'].sum()

  for status_type in status_types:
    df_segment = df[df.status_type == status_type]

    top_items = df_segment[df_segment.num_shares > df_segment.num_shares.quantile(0.95)].fillna(0)

    size_of_top = top_items['num_shares'].sum()
    relative_size_of_top = size_of_top / total_shares

    output.loc[len(output) + 1] = [status_type, relative_size_of_top]

  writeDataFrameToCsv(output)
  # renderChart(output)

def dataframeStats(use_mean = False):

  df = createDataFrame()
  number_of_brands = len(df.page_id.unique())

  print cli.horizontalRule()
  print 'Number of rows: %s' % formatting.humanizeNumber(len(df.index))
  print 'Number of elements: %s' % formatting.humanizeNumber(df.size)
  print 'Number of brands: %s' % number_of_brands

  describe(df)

  time_series = df.resample(resample_period).size()

  if use_mean:
    time_series = time_series.apply(lambda x: x / number_of_brands)

  writeDataFrameToCsv(time_series)
  renderChart(time_series)

def dataframeAverageStats():
  dataframeStats(use_mean = True)

if __name__ == '__main__':
  try:
    globals()[args.action]()
  except AttributeError:
    'Method not found'

  print 'Done!'
