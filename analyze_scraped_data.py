import csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

input_path = "collated_data"

def readCsv(csv_path):

  df = pd.read_csv(csv_path, index_col = False)
  # rng = pd.date_range('1/3/2015', periods = 7, freq = '4M')

  df['Datetime'] = pd.to_datetime(df['status_published'])

  df = df.set_index('Datetime')

  status_type_counts = df.groupby('status_type').resample('4M').size()

  status_type_counts.to_csv('output.csv')

if __name__ == '__main__':
  readCsv("collated_data/2017-04-11_21:02:46.csv")

  print "Done!"
