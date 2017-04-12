import datetime
import csv
import time
import os

dir_path = "scraped_data"
output_dir_path = "collated_data"

collation_starttime = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
output_path = os.path.join(output_dir_path, "%s.csv" % collation_starttime)

output = [] # Todo remove

class Metadata:
  heading_row = None

class Indeces:
  status_id_index = None
  status_message_index = None

def parseRow(row):

  # Add page_id to row

  status_id = row[Indeces.status_id_index]
  row.append(status_id.split("_")[0])

  # Add message length count to row

  status_message = row[Indeces.status_message_index]
  row.append(len(status_message))

  # Add clean domain

  # TODO

  return row


def readDir(dir_path):
  files = os.listdir(dir_path)
  files_length = len(files)

  for index, file in enumerate(files):
    if file.endswith(".csv"):
      file_path = os.path.join(dir_path, file)

      print "%s/%s Parsing %s" % (index + 1, files_length, file_path)

      readCsv(file_path)


def readCsv(csv_filename):

  with open(csv_filename, 'rb') as file:
    reader = csv.reader(file)

    for index, row in enumerate(reader):

      # If it's the heading row, find out which columns data is in

      if index == 0:

        Indeces.status_id_index = row.index("status_id")
        Indeces.status_message_index = row.index("status_message")

        row.append('page_id')
        row.append('status_message_length')

        Metadata.heading_row = row

      # if it's not the heading row, aggregate the data

      else:

        parsed_row = parseRow(row)

        output.append(parsed_row)

if __name__ == '__main__':
  readDir(dir_path)

  print "Creating collated data file"

  with open(output_path, 'wb') as file:
    writer = csv.writer(file)

    output.insert(0, Metadata.heading_row)

    writer.writerows(output)

  print "Finished creating collated data file"
  print "Done!"
