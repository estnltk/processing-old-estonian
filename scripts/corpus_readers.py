from estnltk import Text
import csv
from bs4 import BeautifulSoup
import os
import sys

def read_from_csv(path):
	with open(path, encoding="utf-8") as fin:
		records=[]
		reader=csv.DictReader(fin, delimiter='|', quotechar='"')
		for row in reader:
			#Cleanup the texts from html-tags
			soup=BeautifulSoup(row['text'], "html.parser")
			content=soup.get_text()
			meta={
				'location':row['maakond'],
				'year' : row['year'],
				'id' : row['id']}
			records.append((content, meta))
	return records

def read_from_xml(path):
	records=[]
	if os.path.isdir(path):
		for root, dirs, files in os.walk(path):
			(head, tail) = os.path.split(root)
			if len(files) > 0:
				for file in files:
					if not file.endswith(".xml"):
						continue
					with open(os.path.join(root, file)) as fin:
						content=fin.read()
					soup=BeautifulSoup(content, "lxml")
					content=soup.find("sisu").getText()
					location=soup.find("vald").getText()
					#Sometimes the date is not written
					try:
						date=soup.find("aeg").getText()
						year=date.split(".")[-1]
					except AttributeError:
						year="n.a."
					#Let's get the id from the filename and remove the extension
					record_id=file.split(".")[0]
					meta={'year' : year,
						'location' : location,
						'id':record_id}
					records.append((content, meta))
	return records
def read_corpus(path):
	sys.stderr.write("Reading corpus.\n")
	if os.path.isdir(path):
		records=read_from_xml(path)
	elif os.path.isfile(path):
		if path.endswith("csv"):
			records=read_from_csv(path)
	#In order to display the progress, initialise the counter
	count=0
	#In order not to bombard the stderr, let's initialise the displayed progress value and if it differs from the progress, we will update and display it.
	percent_displayed=""
	progress=""
	for i in records:
		text=Text(i[0])
		text.meta=i[1]
		count+=1
		percent=int(count*100/len(records))
		if percent != percent_displayed:
			percent_displayed=percent
			progress="Working with records "+str(percent_displayed).rjust(3)+"%"
			sys.stderr.write("\r"+progress)
			sys.stderr.flush()

		yield text
	sys.stderr.write("\n")