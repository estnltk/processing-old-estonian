import corpus_readers
import sys
from estnltk import Layer, Text
from estnltk.taggers import DiffTagger
from estnltk.layer_operations import flatten
from estnltk.taggers.text_segmentation.whitespace_tokens_tagger import WhiteSpaceTokensTagger
from estnltk.taggers.morph_analysis.morf_common import _is_empty_annotation
from morph_pipeline import *
from estnltk.taggers import VabamorfAnalyzer
from estnltk import Annotation
import os
import csv



manually_tagged=corpus_readers.read_from_tsv(sys.argv[2])
user_dict_dir=sys.argv[1]
normalized_words_dir=sys.argv[3]
if not os.path.exists(user_dict_dir):
	os.mkdir(user_dict_dir)
#Function gotten from Siim Orasmaa
def remove_attribs_from_layer(text, layer_name, new_layer_name, remove_attribs):
	new_attribs = [a for a in text[layer_name].attributes if a not in remove_attribs] 
	new_layer=Layer(name=new_layer_name,
		text_object=text,
		attributes=new_attribs,		parent=text[layer_name].parent if text[layer_name].parent else None,
		ambiguous=text[layer_name].ambiguous)
	for span in text[layer_name]:
		for annotation in span.annotations:
			analysis = { attrib:annotation[attrib] for attrib in new_attribs}
			new_layer.add_annotation((span.start, span.end), **analysis)
	return new_layer

from morph_eval_utils import get_estnltk_morph_analysis_diff_annotations
from morph_eval_utils import get_estnltk_morph_analysis_annotation_alignments
from morph_eval_utils import get_concise_morph_diff_alignment_str


diff_tagger = DiffTagger(layer_a='manual_morph_flat',
	layer_b='morph_analysis_flat',
	output_layer='diff_layer',
	output_attributes=('span_status', 'root', 'lemma', 'root_tokens', 'ending', 'clitic', 'partofspeech', 'form'),
	span_status_attribute='span_status')
dicts={}
morph_configuration={'add_punctuation_analysis':True, 'tokens_tagger':WhiteSpaceTokensTagger()}
for text in manually_tagged:
	#print (text.meta['id'])
	if text.meta['location'] not in dicts:
		dicts[text.meta['location']]=[]
	text=apply_pipeline(text, morph_configuration)
	morph_analysis_proc=remove_attribs_from_layer(text, 'morph_analysis', 'morph_analysis_processed', ['normalized_text'])
	manual_morph_proc=remove_attribs_from_layer(text, 'manual_morph', 'manual_morph_processed', ['normalized_text'])
	text.add_layer(flatten(morph_analysis_proc, 'morph_analysis_flat'))
	text.add_layer(flatten(manual_morph_proc, 'manual_morph_flat'))
	diff_tagger.tag(text)
	# Get differences grouped by word spans
	ann_diffs_grouped = get_estnltk_morph_analysis_diff_annotations( text, 'manual_morph_flat','morph_analysis_flat', 'diff_layer')
	# Align annotation differences for each word: find common, modified, missing and extra annotations
	focus_attributes=['root', 'partofspeech', 'form'] # which attributes will be displayed
	diff_word_alignments = get_estnltk_morph_analysis_annotation_alignments( ann_diffs_grouped, ['manual_morph_flat','morph_analysis_flat'],focus_attributes=focus_attributes  )
	# Display results word by word
	
	for word_alignment in diff_word_alignments:
		#print (word_alignment)
		for analysis in word_alignment['alignments']:
			#print (analysis)
			if analysis['__status']=='MISSING' or analysis['__status']=='MODIFIED':
				#print (analysis)
				analysis['manual_morph_flat']['text']=word_alignment['text']
				dicts[text.meta['location']].append(analysis['manual_morph_flat'])
				#print (analysis['manual_morph_flat'])
	#print()
	
#Collect the words with their specified standard counterparts.
if os.path.exists(normalized_words_dir):
	vm=VabamorfAnalyzer(guess=False, propername=False)
	for file in os.listdir(normalized_words_dir):
		location=file.replace(".srt", "")
		if location not in dicts:
			dicts[location]=[]
		
		with open(os.path.join(normalized_words_dir, file)) as fin:
			raw_words=[]
			normalized_forms=[]
			for line in fin:	
				line=line.strip()
				line=line.split(" ")
				#The first element of a line is the non-standard word, the other one is the normalized form
				raw_words.append(line[0])
				normalized_forms.append(line[1])
			raw_text=" ".join(raw_words)
			text=Text(raw_text)
			text.tag_layer(['sentences'])
			for index, w in enumerate(text['words']):
				w.clear_annotations()
				w.add_annotation( Annotation(w, normalized_form=normalized_forms[index]) )
			vm.tag(text)
			for w in text['morph_analysis']:
				for annotation in w.annotations:
					annotation['text']=w.text
					dicts[location].append(annotation)

#Write the dicts into tsv files
for location in dicts:
	dict=dicts[location]
	outfile=os.path.join(user_dict_dir, location+".tsv")
	with open(outfile, 'w', encoding='utf-8', newline='\n') as csvfile:
		fieldnames = ['text', 'root', 'ending', 'clitic', 'partofspeech', 'form']
		writer = csv.DictWriter(csvfile, delimiter='\t', fieldnames=fieldnames)
		writer.writeheader() # Write the headers at the beginning
		for analysis in dict:
			row={}
			row['text']=analysis['text']
			row['root']=analysis['root']
			row['ending']=analysis['ending']
			row['clitic']=analysis['clitic']
			row['partofspeech']=analysis['partofspeech']
			row['form']=analysis['form']
			writer.writerow(row)