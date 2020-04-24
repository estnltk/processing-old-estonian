import corpus_readers
import sys
from estnltk import Layer, Text
from estnltk.taggers import VabamorfAnalyzer
from estnltk.taggers import DiffTagger
from estnltk.layer_operations import flatten
from estnltk.taggers.text_segmentation.whitespace_tokens_tagger import WhiteSpaceTokensTagger
from estnltk.taggers.morph_analysis.morf_common import _is_empty_annotation
from morph_pipeline import *
manually_tagged=corpus_readers.read_from_tsv(sys.argv[1])
if len(sys.argv) > 2:
	user_dict_dir=sys.argv[2]
else:
	user_dict_dir=""

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
morph_configuration={'add_punctuation_analysis':False, 'tokens_tagger':WhiteSpaceTokensTagger(), 'user_dictionaries':create_user_dict_taggers(user_dict_dir)}
print ("filename\tprecision\trecall\tf-score\tpercentage of ambiguous words\taverage number of analyses per ambiguous word\ttotal words\ttotal with no punctuation\ttotal number of manually analyzed\tunambiguous\tunambiguous with no punctuation\tambiguous correctly analyzed\tambiguously analyzed total\tambiguous analyses total\tcorrectly analyzed\tincorrectly analyzed\tautomatically analyzed total\tnot automatically analyzed\tnot manually analyzed")
whole_corpus=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
for text in manually_tagged:
	#print (text.meta['id'])
	text=apply_pipeline(text, morph_configuration)
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
	diff_word_alignments = get_estnltk_morph_analysis_annotation_alignments( ann_diffs_grouped, ['manual_morph_flat','morph_analysis_flat'],focus_attributes=focus_attributes  )
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
	ambiguous_correct=0
	incorrectly_analyzed=0
	not_automatically_analyzed=0
	not_manually_analyzed=0
	ambiguous_total=0
	punct=0
	total=0
	ambiguous_analyses=0
	for word in text['manual_morph'].spans:
		total+=1
		#Check if a word is punctuation
		if len(word.text) > 0 and not any([c.isalnum() for c in word.text]):
			punct+=1
		#Check if the loop is at the end of differences.
		if diff_index==len(diff_word_alignments):
			if _is_empty_annotation( word.annotations[0] ):
				manually_not_analyzed+=1
			else:
				unambiguous+=1
			continue
		
		alignments=diff_word_alignments[diff_index]
		#If the word does not exist in the diff layer, then it is unambiguous and analyzed correctly
		if alignments['start'] != word.start and alignments['end'] != word.end and not _is_empty_annotation( word.annotations[0] ):
			unambiguous+=1
			continue
		if _is_empty_annotation( word.annotations[0] ):
			not_manually_analyzed+=1
		
		statuses=[]
		for alignment in alignments['alignments']:
			statuses.append(alignment['__status'])
		if len(statuses) > 1:
			ambiguous_total+=1
			ambiguous_analyses+=len(statuses)

		if 'COMMON' in statuses:
			ambiguous_correct += 1
		elif 'MODIFIED' in statuses:
			incorrectly_analyzed+=1
		elif 'MISSING' in statuses:
			not_automatically_analyzed+=1
		diff_index+=1
	unambiguous_no_punct=unambiguous - punct
	correctly_analyzed=unambiguous_no_punct + ambiguous_correct
	total_no_punct=total - punct
	total_manually_analyzed=total_no_punct - not_manually_analyzed
	analyzed=total_no_punct - not_automatically_analyzed -not_manually_analyzed
	precision=correctly_analyzed /analyzed
	recall=correctly_analyzed/total_manually_analyzed
	f_score=(2 * precision * recall) / (precision + recall)
	ambiguous_percentage=ambiguous_total/total*100
	average_analyses=ambiguous_analyses/ambiguous_total
	row=[precision, recall, f_score, ambiguous_percentage, average_analyses, total, total_no_punct, total_manually_analyzed, unambiguous, unambiguous_no_punct, ambiguous_correct, ambiguous_total, ambiguous_analyses, correctly_analyzed, incorrectly_analyzed, analyzed, not_automatically_analyzed, not_manually_analyzed]
	#convert the elements into strings and also add them to the whole corpus results
	for index, i in enumerate(row):
		whole_corpus[index]+=i
		row[index]=str(round(i, 2))
	print ("\t".join([text.meta['id']] + row))
#To get the average precision, recall and f-score, divide the previously added sums with the number of texts.
whole_corpus[0]=whole_corpus[0]/len(manually_tagged)
whole_corpus[1]=whole_corpus[1]/len(manually_tagged)
whole_corpus[2]=whole_corpus[2]/len(manually_tagged)
whole_corpus[3]=whole_corpus[3]/len(manually_tagged)
whole_corpus[4]=whole_corpus[4]/len(manually_tagged)
for index, i in enumerate(whole_corpus):
	whole_corpus[index]=str(round(i, 2))
print ("\t".join(['Whole corpus'] + whole_corpus))
	