import corpus_readers
import sys
from estnltk import Layer, Text
from estnltk.taggers import VabamorfAnalyzer
from estnltk.taggers import DiffTagger
from estnltk.layer_operations import flatten
manually_tagged=corpus_readers.read_from_tsv(sys.argv[1])
vm_analyzer=VabamorfAnalyzer()

diff_tagger = DiffTagger(layer_a='morph_analysis_flat',
	layer_b='manual_morph_flat',
	output_layer='diff_layer',
	output_attributes=('span_status', 'root', 'lemma', 'root_tokens', 'ending', 'clitic', 'partofspeech', 'form'),
	span_status_attribute='span_status')

for text in manually_tagged:
	#print (text.meta['id'])
	#print (text.morph_analysis[-2])
	text.tag_layer(['sentences'])
	vm_analyzer.tag(text)
	text.add_layer(flatten(text['morph_analysis'], 'morph_analysis_flat'))
	text.add_layer(flatten(text['manual_morph'], 'manual_morph_flat'))
	diff_tagger.tag(text)
	#for word in text.manual_morph:
	#	print (word)
	print (text.diff_layer.meta)
	print (text.diff_layer)