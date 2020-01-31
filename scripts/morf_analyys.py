#!/usr/bin/python3.5
# -*- coding: utf-8 -*-
#   Teostab vallakohtu protokollide morf analüüsi, salvestab tulemused 
#   TSV (tab separated values) failidena ning ühtlasi korjab ja väljastab 
#   analüüsi tulemuste statistika.

from __future__ import unicode_literals, print_function, absolute_import

from estnltk.text import Text
from collections import defaultdict
from bs4 import BeautifulSoup
import re
import csv
import sys, os, os.path
import json
import argparse
from estnltk.vabamorf.morf import disambiguate
from estnltk.resolve_layer_dag import make_resolver
from estnltk.taggers import VabamorfTagger
from estnltk import Text
from estnltk.taggers import VabamorfAnalyzer
from estnltk.taggers.morph_analysis.morf_common import _is_empty_annotation
from estnltk import Annotation
import corpus_readers
# Kas morf analüüsi (TSV) väljundisse tuleks lisada puuduvad punktuatsiooni morf analüüsid?
lisa_punktuatsiooni_analyysid = True
lisa_lausepiirid=False
# Kas statistikast tuleks lahutada punktuatsiooni analüüsid?
lahuta_punktuatsiooni_analyysid = True

# Kas TSV väljundfailidele lisatakse päis?
lisa_tsv_faili_p2is = False
# Leiab, mitu % moodustab c a-st ning vormistab tulemused sõne kujul;
def get_percentage_of_all_str( c, a ):
	return '{} / {} ({:.2f}%)'.format(c, a, (c*100.0)/a)

# Lisab Text objektile punktuatsiooni analüüsi 
# (kuna vaikimisi jäetakse ilma olemiseta ka punktuatsioon analüüsimata)
def add_punctuation_analysis ( text ):
	for word in text.morph_analysis:
		if _is_empty_annotation( word.annotations[0] ):
			# Teeme kindlaks, kas tegemist on punktuatsiooniga
			if len(word.text) > 0 and not any([c.isalnum() for c in word.text]):
				# On punktuatsioon: genereerime oletamisega analüüsid ja lisame
				w=Text(word.text)
				w.tag_layer(['sentences'])
				vm_analyser = VabamorfAnalyzer(guess=True, propername=True)
				vm_analyser.tag(w)
				
				analysis=w.morph_analysis[0].annotations
				# Kui mingil põhjusel peaks analüüs olema mitmene, 
				# jätame alles vaid esimese:
				if len(analysis) > 1:
					analysis = [ analysis[0] ]
					
				#Kirjutame analüüsi üle uuega
				word.clear_annotations()
				word.add_annotation(Annotation(word, **analysis[0]))
				

#Kontrollib ilma analüüsita sõnade puhul, kas w asendamine w-ga ja I J-ga parandab analüüsi
def replace_letters(text):
	for word in text.morph_analysis:
		if _is_empty_annotation( word.annotations[0] ):
			tmp=word.text
			#asendame w v-ga.
			tmp=tmp.replace("w", "v")
			tmp=tmp.replace("W", "V")
			w=Text(tmp)
			w.tag_layer(['sentences'])
			vm_analyser = VabamorfAnalyzer(guess=False, propername=False)
			vm_analyser.tag(w)
			analysis=w.morph_analysis[0].annotations
			if not _is_empty_annotation(analysis[0]):
				word.clear_annotations()
				for a in analysis:
					word.add_annotation(Annotation(word, **a))
				continue
			tmp=word.text
			#Kuna gooti kirjas on suur I ja J samasugused, siis teeme asenduse
			tmp=tmp.replace("I", "J")
			w=Text(tmp)
			w.tag_layer(['sentences'])
			vm_analyser = VabamorfAnalyzer(guess=False, propername=False)
			vm_analyser.tag(w)
			analysis=w.morph_analysis[0].annotations
			if not _is_empty_annotation(analysis[0]):
				word.clear_annotations()
				for a in analysis:
					word.add_annotation(Annotation(word, **a))
				continue
				


# Kirjutab analüüsid TSV (tab-separated-values) failina
def write_analysis_tsv_file( text, out_file_name ):
	global lisa_tsv_faili_p2is
	global lisa_lausepiirid
	# Leiame lausepiirid (kokkuleppeliselt: reavahetused)
	sentence_boundaries = None
	if lisa_lausepiirid:
		
		sentence_boundaries = find_sentence_boundaries(text.text)
		#print (len(sentence_boundaries))
		assert len(sentence_boundaries) > 0
	with open(out_file_name, 'w', encoding='utf-8', newline='\n') as csvfile:
		fieldnames = ['word', 'root', 'ending', 'clitic', 'partofspeech', 'form']
		writer = csv.DictWriter(csvfile, delimiter='\t', fieldnames=fieldnames)
		if lisa_tsv_faili_p2is:
			writer.writeheader() # Lisame algusesse p2ise
		sentence_id = 0
		word_count  = 0
		###
		for word in text.morph_analysis:
			analyses=word.annotations
			# Lause algus
			if lisa_lausepiirid and sentence_boundaries != None and len(sentence_boundaries) > 0:
				sentence_span = sentence_boundaries[sentence_id]
				# Lause algus
				if word.start == sentence_span[0]:
					analysis_item = {}
					analysis_item['word']='<s>'
					analysis_item['root']=''
					analysis_item['ending']=''
					analysis_item['clitic']=''
					analysis_item['partofspeech']=''
					analysis_item['form']=''
					writer.writerow(analysis_item)
			# Väljastame sõna analüüsid (kui neid leidus)
			if not _is_empty_annotation(analyses[0]):
				for aid, analysis in enumerate(analyses):
					analysis_item = {}
					analysis_item['word']=word.text
					analysis_item['root']=analysis['root']
					analysis_item['ending']=analysis['ending']
					analysis_item['clitic']=analysis['clitic']
					analysis_item['partofspeech']=analysis['partofspeech']
					analysis_item['form']=analysis['form']
					if aid > 0:
						analysis_item['word']=' '*len(word.text)
					writer.writerow(analysis_item)
			# Kui analüüse polnudki, väljastame tühja rea
			if _is_empty_annotation(analyses[0]):
				analysis_item = {}
				analysis_item['word']=word.text
				analysis_item['root']='####'
				analysis_item['ending']=''
				analysis_item['clitic']=''
				analysis_item['partofspeech']=''
				analysis_item['form']=''
				writer.writerow(analysis_item)
			# Lause lõpp
			if lisa_lausepiirid and sentence_boundaries != None and len(sentence_boundaries) > 0:
				sentence_span = sentence_boundaries[sentence_id]
				if word.end == sentence_span[1]:
				   analysis_item = {}
				   analysis_item['word']='</s>'
				   analysis_item['root']=''
				   analysis_item['ending']=''
				   analysis_item['clitic']=''
				   analysis_item['partofspeech']=''
				   analysis_item['form']=''
				   writer.writerow(analysis_item)
				   sentence_id += 1
		if lisa_lausepiirid and sentence_boundaries != None and len(sentence_boundaries) > 0:
			assert sentence_id == len(sentence_boundaries), \
			   '(!) Midagi l2ks lausepiiride panemisel viltu failis '+\
			   str(out_file_name)+'; Pandi '+str(sentence_id)+' lausepiiri / '+\
			   'tegelikult oli '+str(len(sentence_boundaries))+' lausepiiri;'



# Leiab sisendteksti (sõne) lausepiirid
# Kokkuleppeliselt: laused on reavahetusega 
# eraldatud
def find_sentence_boundaries( text ):
	
	assert isinstance(text, str) 
	text+="\n"
	results = []
	start = 0
	for char_id, char in enumerate(text):
		if char == '\n':
		   end = char_id
		   # Erand: mõnikord on lause alguses miskipärast tabulaatorid
		   # Parandus: nihutame lause algust nii, et see poleks tabulaator
		   while start < end:
			   start_char = text[start]
			   if not start_char.isspace():
				   break
			   start += 1
		   # Erand: mõnikord on lausepiir miskipärast tabulaatori järel
		   # Parandus: nihutame lause lõppu nii, et lõpus oleks sõna, mitte tabulaator
		   while start < end-1:
			   end_char = text[end-1]
			   if not end_char.isspace():
				   break
			   end -= 1
		   if start < end:
			   results.append( (start, end) )
		   start = end + 1
	#print (results)
	return results


infile=sys.argv[1]
outputdir=sys.argv[2]

#	 (records, analysed, unamb, unk_title, unk_punct, punct, total)
def process_location():
	global lisa_punktuatsiooni_analyysid
	records=defaultdict(int)
	analysed=defaultdict(int)
	unamb=defaultdict(int)
	total=defaultdict(int)
	unk_title=defaultdict(int)
	unk_punct=defaultdict(int)
	punct=defaultdict(int)
	decades_analysed=defaultdict(lambda: defaultdict(int))
	decades_total=defaultdict(lambda: defaultdict(int))
	freq_analysed=defaultdict(lambda: defaultdict(int))
	freq_not_analysed=defaultdict(lambda: defaultdict(int))
	texts=corpus_readers.read_corpus(infile)
	for text in texts:
		location=text.meta['location']
		text.tag_layer(['sentences'])
		records[location]+=1
		#Muudame aastaarvu kümnendiks
		decade=text.meta['year'][:-1]+"0"
		vm_analyser = VabamorfAnalyzer(guess=False, propername=False)
		vm_analyser.tag(text)
		
		# Teostame järelparandused
		if lisa_punktuatsiooni_analyysid:
			add_punctuation_analysis( text )
		replace_letters(text)
		# Kogume kokku statistika
		for word in text.morph_analysis:
			is_punct = len(word.text) > 0 and not any([c.isalnum() for c in word.text])
			if not _is_empty_annotation( word.annotations[0] ):
				analysed[location] += 1
				decades_analysed[location][decade]+=1
				if not is_punct:
					freq_analysed[location][word.text]+=1
				if len(word.annotations) == 1:
					unamb[location] += 1
			if _is_empty_annotation( word.annotations[0] ):
				freq_not_analysed[location][word.text]+=1
				# Jäädvustame tundmatu sõna tüübi
				
				if len(word.text) > 0:
					if word.text[0].isupper():
						unk_title[location] += 1
					if is_punct:
						unk_punct[location] += 1
			else:
				# Jäädvustame tavalise sõna tüübi
				if is_punct:
					punct[location] += 1
			total[location] += 1
			decades_total[location][decade]+=1
		# Kirjutame morf analüüsid TSV faili
		if not os.path.exists(os.path.join(outputdir, text.meta['location'])):
			os.mkdir(os.path.join(outputdir, text.meta['location']))
		out_file_name = os.path.join(outputdir, text.meta['location'], str(text.meta['id'])+'.tsv')
		write_analysis_tsv_file( text, out_file_name )
	#Agregate the statistics
	results={}
	for location in records:
		if records[location] > 0:
			# Korrigeerimised
			if lahuta_punktuatsiooni_analyysid:
				if lisa_punktuatsiooni_analyysid:
					# Kui oletamine välja lülitada, siis jääb ka punktuatsioon 
					# analüüsita. Lahutame selle sõnadest maha:
					total[location] -= punct[location]
					analysed[location] -= punct[location]
					unamb[location] -= punct[location]
					punct[location] = 0
				else:
					# Kui oletamine välja lülitada, siis jääb ka punktuatsioon 
					# analüüsita. Lahutame selle sõnadest maha:
					total[location] -= unk_punct[location]
					unk_punct[location] = 0
			percent_analysed = (analysed[location] * 100.0) / total[location]
			results_tuple = (records[location], analysed[location], unamb[location], unk_title[location], unk_punct[location], total[location], percent_analysed)
			results[location]=results_tuple
	return results, decades_analysed, decades_total, freq_analysed, freq_not_analysed


# >>> Siit algab programm
results_dict, decades_analysed, decades_total, freq_analysed, freq_not_analysed = process_location()

# Sorteerime tulemused analüüsitute protsendi järgi;
# Väljastame pingerea
#print (results_dict)
#print (type(results_dict['Viru']))
aggregated = [0, 0, 0, 0, 0, 0, 0]
for key in sorted(results_dict, key = lambda x : results_dict[x][-1], reverse=True):
	(records, analysed, unamb, unk_title, unk_punct, total, percent_analysed) = results_dict[key]
	print(' '+key+' (',records,' protokolli )')
	print('	1. morf analüüsiga: '+get_percentage_of_all_str( analysed, total ))
	print('			 sh ühesed: '+get_percentage_of_all_str( unamb, analysed ))
	print('	2. morf analüüsita: '+get_percentage_of_all_str( (total-analysed), total ))
	print('  sh suure algustähega: '+get_percentage_of_all_str( unk_title,(total-analysed) ))
	if not lahuta_punktuatsiooni_analyysid:
		print('	  sh punkuatsioon: '+get_percentage_of_all_str( unk_punct,(total-analysed) ))
	print()
	for i in range(len(results_dict[key])):
		aggregated[i] += results_dict[key][i]
print()
print()
# Väljastame koondtulemuse
print(' Kogu korpuse koondtulemus: ')
[records, analysed, unamb, unk_title, unk_punct, total, percent_analysed] = aggregated
print('	1. morf analüüsiga: '+get_percentage_of_all_str( analysed, total ))
print('			 sh ühesed: '+get_percentage_of_all_str( unamb, analysed ))
print('	2. morf analüüsita: '+get_percentage_of_all_str( (total-analysed), total ))
print('  sh suure algustähega: '+get_percentage_of_all_str( unk_title,(total-analysed) ))
if not lahuta_punktuatsiooni_analyysid:
	print('	  sh punkuatsioon: '+get_percentage_of_all_str( unk_punct,(total-analysed) ))

print ()
print ()
#Kuvab morf statistika maakondade kaupa
print ("maakond\t", end="")
for i in range(1820, 1930, 10):
	print (i, "\t\t\t", end="")
print()
decades_sum=(defaultdict(int), defaultdict(int))
for location in results_dict:
	print (location, "\t", end="")
	for decade in range(1820, 1930, 10):
		decade=str(decade)
		if decade not in decades_total[location] or decades_total[location][decade]==0:
			print ("0\t0\t0%\t", end="")
		else:
			percentage=decades_analysed[location][decade]/decades_total[location][decade]*100
			print (decades_analysed[location][decade], "\t", decades_total[location][decade], "\t", round(percentage, 2), "\t", end="")
		decades_sum[0][decade] += decades_analysed[location][decade]
		decades_sum[1][decade] += decades_total[location][decade]
	print ()
print ("Kokku\t", end="")
for decade in range(1820, 1930, 10):
	decade=str(decade)
	if decade not in decades_sum[1] or decades_sum[1][decade]==0:
		print ("0\t0\t0%\t", end="")
	else:
		percentage=decades_sum[0][decade]/decades_sum[1][decade]*100
		print (decades_sum[0][decade], "\t", decades_sum[1][decade], "\t", round(percentage, 2), "\t", end="")

print()
print()
print ("30 sagedasemat analüüsitud ja analüüsimata sõna maakondade kaupa")
#Tundmatuks jäänud sõnade loend eraldi faili kirjutamiseks
unknown=[]
for location in freq_analysed:
	print (location, end="")
	sorted_analysed=sorted(freq_analysed[location].items(), key=lambda item: item[1], reverse=True)
	#sorted_analysed.reverse()
	sorted_not_analysed=sorted(freq_not_analysed[location].items(), key=lambda item: item[1], reverse=True)
	#sorted_not_analysed.reverse()
	for i in range(30):
		a=sorted_analysed[i]
		b=sorted_not_analysed[i]
		print ("\t", a[0], "\t", a[1], "\t", b[0], "\t", b[1])
		unknown.append(b[0])
	print ("\tUnikaalseid sõnu\t", len(sorted_analysed), "\t\t", len(sorted_not_analysed))
	hapax_analysed=0
	for i in sorted_analysed:
		if i[1]==1:
			hapax_analysed+=1
	hapax_not_analysed=0
	for i in sorted_not_analysed:
		if i[1]==1:
			hapax_not_analysed+=1
	print ("\tHapax legomena\t", hapax_analysed, "\t\t", hapax_not_analysed)


unknown=set(unknown)
with open("tundmatud_sonad.txt", "w") as fout:
	for i in unknown:
		fout.write(i+"\n")