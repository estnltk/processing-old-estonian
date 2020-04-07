from estnltk import Text
import csv
from bs4 import BeautifulSoup
import os
import sys
import re
from estnltk.taggers.text_segmentation.whitespace_tokens_tagger import WhiteSpaceTokensTagger
from estnltk.taggers.text_segmentation.pretokenized_text_compound_tokens_tagger import PretokenizedTextCompoundTokensTagger

from estnltk import Layer

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
					with open(os.path.join(root, file), encoding="utf-8") as fin:
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

def read_from_tsv(path):
	texts=[]
	tokens_tagger = WhiteSpaceTokensTagger()
	if os.path.isdir(path):
		for root, dirs, files in os.walk(path):
			(head, tail) = os.path.split(root)
			if len(files) > 0:
				for file in files:
					if not file.endswith(".tsv"):
						continue
					with open(os.path.join(root, file), encoding="utf-8") as fin:	
						reader=csv.reader(fin, delimiter='\t')
						words=[]
						#Lines containing a word and its' analysis
						word=[]
						#Morphological analysis of the whole text.
						morph_analysis=[]
						raw_text=""
						multiword_expressions = []
						
						for row in reader:
							row[0]=row[0].strip()
							#If the first element of a row is empty then it is an alternative analysis of a word.
							if row[0]=="" and word:
								word.append(row)
							else:
								if len(word) != 0:
									words.append(word)
								#After appending the word into the words list let's initialize a new word.
								word=[row]
						for word in words:
							#Iterate over the analyses and check for manual fixes.
							#Remove all other analyses if they exist.
							for analysis in word:
								if "¤" in analysis:
									word[0][1:]=["¤", "", "", "", ""]
									word=[word[0]]
								elif analysis[1].startswith("@"):
									word[0][1:]=analysis[1:]
									word=[word[0]]
								elif analysis[1].startswith("£"):
									word[0][1:]=analysis[1:]
									word=[word[0]]
								elif re.match("#[A-Üa-ü0-9]", analysis[1]):
									word[0][1:]=analysis[1:]
									word=[word[0]]
								elif analysis[1].startswith("###"):
									word_tuple=(word[0][0], [])
									
									morph_analysis.append(word_tuple)
									raw_text+=word[0][0]+" "
									if ' ' in word[0][0]:
										multiword_expressions.append(word[0][0])
									continue
							analyses=[]
							for a in word:
								analysis={}
								analysis['root']=a[1]
								#Clear the fixing symbols from the root
								analysis['root']=re.sub(r'#|£@', '', analysis['root'])
								#If it is an abbreviation some fields may be missing.
								#Sometimes there are also missing tabs in the end of a line, so the last element has to be checked.
								if a[-1]=="Y" or a[-1]=='D' or a[-1]=='K':
									analysis['partofspeech']="Y"
									analysis['ending']=""
									analysis['form']=""
									analysis['clitic']=""
								else:
									analysis['ending']=a[2]
									analysis['clitic']=a[3]
									analysis['partofspeech']=a[4]
									analysis['form']=a[5] if len(a) ==6 else ""
								analysis['root_tokens']=[analysis['root']]
								analysis['lemma']=analysis['root']
								#Will be implemented
								analysis['type_of_fix']=""
								analyses.append(analysis)
							word_tuple=(word[0][0], analyses)
							morph_analysis.append(word_tuple)
							raw_text+=word[0][0]+" "
							if ' ' in word[0][0]:
								multiword_expressions.append(word[0][0])
						text = Text(raw_text)
						
						tokens_tagger.tag(text)
						multiword_expressions = [mw.split() for mw in multiword_expressions]
						compound_tokens_tagger = PretokenizedTextCompoundTokensTagger( multiword_units = multiword_expressions )
						compound_tokens_tagger.tag(text)
						text.tag_layer(['sentences'])
						layer=Layer(name='morph_analysis',
							text_object=text,
							attributes=['root', 'lemma', 'root_tokens', 'ending', 'clitic', 'partofspeech', 'form', 'type_of_fix', 'normalized_form'],
							parent='words',
							ambiguous=True)
						for ind, word in enumerate(text.words):
							for analysis in morph_analysis[ind][1]:
								layer.add_annotation((word.start, word.end), **analysis)
						text.add_layer(layer)
						text.meta['id']=file.split(".")[0]
						texts.append(text)
	return texts



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
		text=i[0].replace("\n\n", "\n")
		#text=text.replace(chr(10), "")
		#text = os.linesep.join([s for s in text.splitlines() if s])
		text=Text(text)
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