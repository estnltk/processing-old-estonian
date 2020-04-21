import corpus_readers
import sys
from estnltk import Layer, Text
from estnltk.taggers import VabamorfAnalyzer
from estnltk.taggers import DiffTagger
from estnltk.layer_operations import flatten
from morph_tagger import *
manually_tagged=corpus_readers.read_from_tsv(sys.argv[1])
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

#vm_analyzer=VabamorfAnalyzer(guess=False, propername=False)
#vm_analyzer=VabamorfAnalyzer()

diff_tagger = DiffTagger(layer_a='manual_morph_flat',
	layer_b='morph_analysis_flat',
	output_layer='diff_layer',
	output_attributes=('span_status', 'root', 'lemma', 'root_tokens', 'ending', 'clitic', 'partofspeech', 'form'),
	span_status_attribute='span_status')
print ("filename\tprecision\trecall\ttotal\ttotal with no punctuation\tunambiguous\tunambiguous with no punctuation\tambiguous\tcorrect analyses\tincorrect analyses\tno analyses")

for text in manually_tagged:
	#print (text.meta['id'])
	#text.tag_layer(['sentences'])
	#vm_analyzer.tag(text)
	text=morph_tagger(text, {'add_punctuation_analysis':False})
	morph_analysis_proc=remove_attribs_from_layer(text, 'morph_analysis', 'morph_analysis_processed', ['normalized_text'])
	manual_morph_proc=remove_attribs_from_layer(text, 'manual_morph', 'manual_morph_processed', ['normalized_text'])
	text.add_layer(flatten(morph_analysis_proc, 'morph_analysis_flat'))
	text.add_layer(flatten(manual_morph_proc, 'manual_morph_flat'))
	diff_tagger.tag(text)
	#for word in text.manual_morph:
	#	print (word)
	#print ("***", text.meta['id'], text.diff_layer.meta)
	#print (text.diff_layer)

	# Get differences grouped by word spans
	ann_diffs_grouped = get_estnltk_morph_analysis_diff_annotations( text, 'manual_morph_flat','morph_analysis_flat', 'diff_layer')
	# Align annotation differences for each word: find common, modified, missing and extra annotations
	focus_attributes=['root', 'partofspeech', 'form'] # which attributes will be displayed
	diff_word_alignments = get_estnltk_morph_analysis_annotation_alignments( ann_diffs_grouped, ['morph_analysis_flat','manual_morph_flat'],focus_attributes=focus_attributes  )
	# Display results word by word
	"""
	for word_alignment in diff_word_alignments:
		align_str = get_concise_morph_diff_alignment_str(word_alignment['alignments'], 'morph_analysis_flat','manual_morph_flat',focus_attributes=focus_attributes)
		print('{!r}'.format( word_alignment['text']) )
		print(align_str)
		#print (word_alignment)
	#print()
	"""
	diff_index=0
	unambiguous=0
	ambiguous=0
	incorrect_analyses=0
	no_analyses=0
	punct=0
	total=0
	for word in text['morph_analysis'].spans:
		if diff_index==len(diff_word_alignments):
			break
		total+=1
		#Check if a word is punctuation
		if len(word.text) > 0 and not any([c.isalnum() for c in word.text]):
			punct+=1
		
		alignments=diff_word_alignments[diff_index]
		if alignments['start'] != word.start and alignments['end'] != word.end:
			unambiguous+=1
			continue
		statuses=[]
		for alignment in alignments['alignments']:
			statuses.append(alignment['__status'])
		if 'COMMON' in statuses:
			ambiguous+=1
		elif 'MODIFIED' in statuses:
			incorrect_analyses+=1
		elif 'MISSING' in statuses:
			no_analyses+=1
		diff_index+=1
	correct_analyses=unambiguous + ambiguous - punct
	unambiguous_no_punct=unambiguous - punct
	total_no_punct=total - punct
	analyzed=total_no_punct - no_analyses
	precision=correct_analyses /analyzed
	recall=analyzed/total_no_punct
	row=[precision, recall, total, total_no_punct, unambiguous, unambiguous_no_punct, ambiguous, correct_analyses, incorrect_analyses, no_analyses]
	#convert the elements into strings
	for index, i in enumerate(row):
		row[index]=str(round(i, 2))
		
	print ("\t".join([text.meta['id']] + row))