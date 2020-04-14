#!/usr/bin/python3.5
# -*- coding: utf-8 -*-
#Performs the morphological analysis of municipal court records,
#saves the results as .tsv files
#and outputs the statistics to standard output.
#The progress of the script is output to stderr

from __future__ import unicode_literals, print_function, absolute_import

from estnltk.text import Text
from collections import defaultdict
from bs4 import BeautifulSoup
import csv
import sys, os, os.path
import argparse
from estnltk.taggers import VabamorfAnalyzer
from estnltk.taggers.morph_analysis.morf_common import _is_empty_annotation
from estnltk import Annotation
from estnltk.taggers import SentenceTokenizer
from nltk.tokenize.simple import LineTokenizer
from estnltk.taggers import TokensTagger
from estnltk.taggers import CompoundTokenTagger
from estnltk.taggers.text_segmentation.whitespace_tokens_tagger import WhiteSpaceTokensTagger
from estnltk.taggers.text_segmentation.pretokenized_text_compound_tokens_tagger import PretokenizedTextCompoundTokensTagger
from estnltk.taggers import Retagger
from estnltk.taggers import UserDictTagger
import corpus_readers
# If the missing punctuation analysis should be added to the tsv output
add_punctuation_analyses = True
add_sentence_boundaries=False
#If the punctuation analyses should be subtracted from the statistics

subtract_punctuation_analyses = True

# If the headers should be added to the tsv files
add_tsv_headers = False
#If alphabet corrections should be performed
prenormalize=True
use_user_dictionary=True

#Finds how many percents C constitutes from A and formats the results as string
def get_percentage_of_all_str( c, a ):
	return '{} / {} ({:.2f}%)'.format(c, a, (c*100.0)/a)

# Adds punctuation analysis to the text object.
# Because punctuation is not analysed when guessing is disabled
def add_punctuation_analysis ( text ):
	#Redefine the tagger for analysing punctuation
	punct_analyser = VabamorfAnalyzer(guess=True, propername=True)
	for word in text.morph_analysis:
		if _is_empty_annotation( word.annotations[0] ):
			# Check if it is punctuation
			if len(word.text) > 0 and not any([c.isalnum() for c in word.text]):
				# It is a punctuation. Generate the analyses with guessing enabled and add them to the text
				w=Text(word.text)
				w.tag_layer(['sentences'])
				punct_analyser.tag(w)
				
				analysis=w.morph_analysis[0].annotations
				# If for some reason there are multiple analyses
				# the only first one will remain.
				if len(analysis) > 1:
					analysis = [ analysis[0] ]
					
				#Rewrite the analysis
				word.clear_annotations()
				word.add_annotation(Annotation(word, **analysis[0]))
				

#Corrects the differences related to the alphabet. Expects letters as character sequences
#w word, x letters to be replaced, y letters replaced with
def alphabet_corrector(w, x, y):
	old=w.text
	normalized=[old]
	#Check if there are already normalized forms present
	if w.normalized_form[0]!=None:
		normalized+=w.normalized_form
	#Iterate over the forms and append the new ones
	for form in normalized:
		new=form.replace(x, y)
		if new!=form:
			normalized.append(new)
	#If only the input form is in the list, then there are no normalized forms added
	if len(normalized)>1:
		w.clear_annotations()
		for form in normalized:
			w.add_annotation( Annotation(w, normalized_form=form) )
	return w


# Writes the analyses as tsv files
def write_analysis_tsv_file( text, out_file_name ):
	global add_tsv_headers
	global add_sentence_boundaries
	# Let's find the sentence boundaries. Newlines.
	sentence_boundaries = None
	if add_sentence_boundaries:
		
		sentence_boundaries = find_sentence_boundaries(text.text)
		assert len(sentence_boundaries) > 0
	with open(out_file_name, 'w', encoding='utf-8', newline='\n') as csvfile:
		fieldnames = ['word', 'root', 'ending', 'clitic', 'partofspeech', 'form']
		writer = csv.DictWriter(csvfile, delimiter='\t', fieldnames=fieldnames)
		if add_tsv_headers:
			writer.writeheader() # Write the headers at the beginning
		sentence_id = 0
		word_count  = 0
		
		for word in text.morph_analysis:
			analyses=word.annotations
			# Beginning of sentence
			if add_sentence_boundaries and sentence_boundaries != None and len(sentence_boundaries) > 0:
				sentence_span = sentence_boundaries[sentence_id]
				# Beginning of sentence
				if word.start == sentence_span[0]:
					analysis_item = {}
					analysis_item['word']='<s>'
					analysis_item['root']=''
					analysis_item['ending']=''
					analysis_item['clitic']=''
					analysis_item['partofspeech']=''
					analysis_item['form']=''
					writer.writerow(analysis_item)
			# Output the word analyses, if they exist
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
			# If there are no analyses, output the empty line
			if _is_empty_annotation(analyses[0]):
				analysis_item = {}
				analysis_item['word']=word.text
				analysis_item['root']='####'
				analysis_item['ending']=''
				analysis_item['clitic']=''
				analysis_item['partofspeech']=''
				analysis_item['form']=''
				writer.writerow(analysis_item)
			# End of sentence
			if add_sentence_boundaries and sentence_boundaries != None and len(sentence_boundaries) > 0:
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
		if add_sentence_boundaries and sentence_boundaries != None and len(sentence_boundaries) > 0:
			#if sentence_id != len(sentence_boundaries):
	#			print ("Midagi läks lausepiiride panemisel viltu failis ", out_file_name, "; pandi ", sentence_id, " lausepiiri. Tegelikult oli ", len(sentence_boundaries), "lausepiiri.")
			assert sentence_id == len(sentence_boundaries), \
			  '(!) Midagi l2ks lausepiiride panemisel viltu failis '+\
			   str(out_file_name)+'; Pandi '+str(sentence_id)+' lausepiiri / '+\
			   'tegelikult oli '+str(len(sentence_boundaries))+' lausepiiri;'



# Finds the sentence boundaries of input text
# The sentences are separated by a newline.
def find_sentence_boundaries( text ):
	
	assert isinstance(text, str) 
	text+="\n"
	results = []
	start = 0
	for char_id, char in enumerate(text):
		if char == '\n':
		   end = char_id
		   # Except sometimes there are tabs in the beginning of sentences
		   # Shift the beginning of sentence
		   while start < end:
			   start_char = text[start]
			   if not start_char.isspace():
				   break
			   start += 1
		   # Sometimes there is a tab after sentence boundary
		   while start < end-1:
			   end_char = text[end-1]
			   if not end_char.isspace():
				   break
			   end -= 1
		   if start < end:
			   results.append( (start, end) )
		   start = end + 1
	return results

def find_sentence_boundaries_alt(text):
	results=[]
	for sentence in text['sentences']:
		results.append((sentence.start, sentence.end))
	return results

class word_prenormalizer( Retagger ):
    """A prenormalizer that replaces some letters that were used in the old writing system with the ones used in contemporary system"""
    conf_param = ['letters_replaced']
    
    def __init__(self):
        # Set input/output layers
        self.input_layers = ['words']
        self.output_layer = 'words'
        self.output_attributes = ['normalized_form', 'is_normalized']
        # Set other configuration parameters
        self.letters_replaced = {'W':'V', 'w':'v', 'I':'j'}
    
    def _change_layer(self, text, layers, status):
        # Get changeble layer
        changeble_layer = layers[self.output_layer]
        # Add new attribute to the layer
        changeble_layer.attributes += (self.output_attributes[-1], )
        # Iterate over words and add new normalizations
        for span in changeble_layer:
            # Get current normalized forms of the word
            current_norm_forms = [a['normalized_form'] for a in span.annotations]
            if current_norm_forms == [None]:
                current_norm_forms = [span.text]
            # Try to replace current normalized forms with forms from the lexicon
            new_forms = []
            change_status = []
            for cur_form in current_norm_forms:
                for letter in self.letters_replaced:
                    new_form=cur_form.replace(letter, self.letters_replaced[letter])
                    if new_form != cur_form:
                        new_forms.append(new_form)
                        change_status.append(True)
                    else:
                        new_forms.append(cur_form)
                        change_status.append(False)
            # Clear existing annotations and add new ones that have 1 extra attribute
            span.clear_annotations()
            for form_id, new_form in enumerate( new_forms ):
                span.add_annotation( Annotation(span, normalized_form=new_form, 
                                                      is_normalized=change_status[form_id]) )

infile=sys.argv[1]
outputdir=sys.argv[2]
if not os.path.exists(outputdir):
	os.mkdir(outputdir)
if use_user_dictionary:
	user_dict_dir=sys.argv[3]

#	 (records, analysed, unamb, unk_title, unk_punct, punct, total)
def process_location():
	vm_analyser = VabamorfAnalyzer(guess=False, propername=False)
	newline_sentence_tokenizer = SentenceTokenizer( base_sentence_tokenizer=LineTokenizer() )
	tokens_tagger = WhiteSpaceTokensTagger()
	prenormalizer=word_prenormalizer()
	global add_punctuation_analyses
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
		#For testing the pretokenized functions
		txt=text.text
		multiword_expressions = []
		raw_words = txt.split(' ')
		for raw_word in raw_words:
			if ' ' in raw_word:
				multiword_expressions.append(raw_token)
		text_str = ' '.join(raw_words)
		meta=text.meta
		text=Text(text_str)
		text.meta=meta
		
		TokensTagger().tag(text)
		multiword_expressions = [mw.split() for mw in multiword_expressions]
		compound_tokens_tagger = PretokenizedTextCompoundTokensTagger( multiword_units = multiword_expressions )
		compound_tokens_tagger.tag(text)
		#CompoundTokenTagger(tag_initials = False).tag(text)
		#text.tag_layer(['sentences'])
		text.tag_layer(['words'])
		newline_sentence_tokenizer.tag(text)
		if prenormalize:
			prenormalizer.retag(text)
		
		records[location]+=1
		#Change the year into decade
		decade=text.meta['year'][:-1]+"0"
		#Correct the alphabet
		#if correct_alphabet:
		#	for word in text.words:
		#		word=alphabet_corrector(word, "W", "V")
		#		word=alphabet_corrector(word, "w", "v")
		#		word=alphabet_corrector(word, "I", "J")
		vm_analyser.tag(text)
		
		# Perform the fixes
		if use_user_dictionary:
			userdict = UserDictTagger()
			user_dict_location_file=os.path.join(user_dict_dir, text.meta['location']+".tsv")
			user_dict_global_file=os.path.join(user_dict_dir, 'global.tsv')
			if os.path.exists(user_dict_location_file):
				userdict.add_words_from_csv_file(user_dict_location_file, encoding='utf-8', delimiter='\t')
			if os.path.exists(user_dict_global_file):
				userdict.add_words_from_csv_file(user_dict_global_file, encoding='utf-8', delimiter='\t')
			userdict.retag(text)
		if add_punctuation_analyses:
			add_punctuation_analysis( text )
		# Collect the statistics
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
				# save the type of unknown word
				
				if len(word.text) > 0:
					if word.text[0].isupper():
						unk_title[location] += 1
					if is_punct:
						unk_punct[location] += 1
			else:
				# Save the type of regular word
				if is_punct:
					punct[location] += 1
			total[location] += 1
			decades_total[location][decade]+=1
		# Write the morph analyses into tsv files
		if not os.path.exists(os.path.join(outputdir, text.meta['location'])):
			os.mkdir(os.path.join(outputdir, text.meta['location']))
		out_file_name = os.path.join(outputdir, text.meta['location'], str(text.meta['id'])+'.tsv')
		write_analysis_tsv_file( text, out_file_name )
	#Agregate the statistics
	results={}
	for location in records:
		if records[location] > 0:
			# Corrections
			if subtract_punctuation_analyses:
				if add_punctuation_analyses:
					# The punctuation won't be analysed if guessing is disabled
					total[location] -= punct[location]
					analysed[location] -= punct[location]
					unamb[location] -= punct[location]
					punct[location] = 0
				else:
					# If guessing is disabled, the punctuation won't be analysed.
					total[location] -= unk_punct[location]
					unk_punct[location] = 0
			percent_analysed = (analysed[location] * 100.0) / total[location]
			results_tuple = (records[location], analysed[location], unamb[location], unk_title[location], unk_punct[location], total[location], percent_analysed)
			results[location]=results_tuple
	return results, decades_analysed, decades_total, freq_analysed, freq_not_analysed



results_dict, decades_analysed, decades_total, freq_analysed, freq_not_analysed = process_location()

# Sort the results according to percentages
# Output the results
#print (type(results_dict['Viru']))
aggregated = [0, 0, 0, 0, 0, 0, 0]
for key in sorted(results_dict, key = lambda x : results_dict[x][-1], reverse=True):
	(records, analysed, unamb, unk_title, unk_punct, total, percent_analysed) = results_dict[key]
	print(' '+key+' (',records,' protokolli )')
	print('	1. morf analüüsiga: '+get_percentage_of_all_str( analysed, total ))
	print('			 sh ühesed: '+get_percentage_of_all_str( unamb, analysed ))
	print('	2. morf analüüsita: '+get_percentage_of_all_str( (total-analysed), total ))
	print('  sh suure algustähega: '+get_percentage_of_all_str( unk_title,(total-analysed) ))
	if not subtract_punctuation_analyses:
		print('	  sh punkuatsioon: '+get_percentage_of_all_str( unk_punct,(total-analysed) ))
	print()
	for i in range(len(results_dict[key])):
		aggregated[i] += results_dict[key][i]
print()
print()
# Output the results for whole corpus
print(' Kogu korpuse koondtulemus: ')
[records, analysed, unamb, unk_title, unk_punct, total, percent_analysed] = aggregated
print('	1. morf analüüsiga: '+get_percentage_of_all_str( analysed, total ))
print('			 sh ühesed: '+get_percentage_of_all_str( unamb, analysed ))
print('	2. morf analüüsita: '+get_percentage_of_all_str( (total-analysed), total ))
print('  sh suure algustähega: '+get_percentage_of_all_str( unk_title,(total-analysed) ))
if not subtract_punctuation_analyses:
	print('	  sh punkuatsioon: '+get_percentage_of_all_str( unk_punct,(total-analysed) ))

print ()
print ()
#Output the results by location and decade
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
#List of unknown words for outputting them into file
unknown=[]
for location in freq_analysed:
	print (location, end="")
	sorted_analysed=sorted(freq_analysed[location].items(), key=lambda item: item[1], reverse=True)
	sorted_not_analysed=sorted(freq_not_analysed[location].items(), key=lambda item: item[1], reverse=True)
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