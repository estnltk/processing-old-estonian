import sys
import os
import json
import csv
inputfile=sys.argv[1]
outputdir=sys.argv[2]
with open (inputfile) as fin:
	user_dict_json=json.loads(fin.read())
for location in user_dict_json:
	outfile=os.path.join(outputdir, location+".tsv")
	with open(outfile, 'w', encoding='utf-8', newline='\n') as csvfile:
		fieldnames = ['text', 'root', 'ending', 'clitic', 'partofspeech', 'form']
		writer = csv.DictWriter(csvfile, delimiter='\t', fieldnames=fieldnames)
		writer.writeheader() # Write the headers at the beginning
		for word in user_dict_json[location]:
			analyses=user_dict_json[location][word]
			for analysis in analyses:
				#print ("test", analysis)
				#sometimes the lemmas happen to be missing
				if 'lemma' in analysis:
					#Skip the pseudo analyses
					if "###" in analysis['lemma']:
						continue
				row={}
				row['text']=word
				row['root']=analysis['root']
				row['ending']=analysis['ending']
				row['clitic']=analysis['clitic']
				row['partofspeech']=analysis['partofspeech']
				row['form']=analysis['form']
				writer.writerow(row)
				
