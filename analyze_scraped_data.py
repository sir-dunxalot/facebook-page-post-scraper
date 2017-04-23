import argparse
import csv
import datetime
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

from fixtures import pages_to_parse
from lib import formatting

# Options

input_path = 'data/scraped'
output_path = 'data/analyzed'

# End of options

# Parse arguments given via the CLI

parser = argparse.ArgumentParser(description = 'Options for analyzing data from FB')

parser.add_argument('action', help = 'The name of the analysis method to run')
parser.add_argument('--output', action = 'store_true', help = 'When present, analysis will be outputted into a CSV file', default = False)
parser.add_argument('--period', help = 'The resample period to use for grouping data', default = 'M')
parser.add_argument('--chart', help = 'The type of chart you would like to plot')
parser.add_argument('--page', help = 'The name of an individual page you would like to run analysis for')

args = parser.parse_args()

resample_period = args.period
chart = args.chart

def writeDataFrameToCsv(df):
  print df

  if args.output:
    write_starttime = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    output_file_path = os.path.join(output_path, '%s_%s.csv' % (args.action, write_starttime))

    df.to_csv(output_file_path)

    print 'Analysis written to %s' % output_file_path

def renderChart(df):
  if args.chart:
    df.plot[chart]()
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

def postLengths():

  df = createDataFrame()

  df['message_length'] = df['status_message'].astype(str).apply(len)

  grouped_lengths = df.resample(resample_period).mean()['message_length']

  writeDataFrameToCsv(grouped_lengths)
  renderChart(grouped_lengths)

def postLengthsGroupByType():

  df = createDataFrame()

  df['message_length'] = df['status_message'].astype(str).apply(len)

  grouped_lengths = df.groupby('status_type').resample(resample_period).mean()['message_length']

  formatted_grouped_lengths = grouped_lengths.unstack(level = 0).fillna(0)

  writeDataFrameToCsv(formatted_grouped_lengths)
  renderChart(formatted_grouped_lengths)

def getDataframeStats():

  df = createDataFrame()

  print '----------------------------'
  print 'Number of rows: %s' % formatting.humanizeNumber(len(df.index))
  print 'Number of elements: %s' % formatting.humanizeNumber(df.size)
  print '----------------------------'

  time_series = df.resample(resample_period).size()

  writeDataFrameToCsv(time_series)
  renderChart(time_series)

if __name__ == '__main__':
  try:
    globals()[args.action]()
  except AttributeError:
    'Method not found'

  print 'Done!'
