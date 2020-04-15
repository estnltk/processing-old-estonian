import corpus_readers
import sys
from estnltk import Layer, Text
from estnltk.taggers import VabamorfAnalyzer
from estnltk.taggers import DiffTagger
from estnltk.layer_operations import flatten
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

vm_analyzer=VabamorfAnalyzer()

diff_tagger = DiffTagger(layer_a='morph_analysis_flat',
	layer_b='manual_morph_flat',
	output_layer='diff_layer',
	output_attributes=('span_status', 'root', 'lemma', 'root_tokens', 'ending', 'clitic', 'partofspeech', 'form'),
	span_status_attribute='span_status')

for text in manually_tagged:
	#print (text.meta['id'])
	text.tag_layer(['sentences'])
	vm_analyzer.tag(text)
	morph_analysis_proc=remove_attribs_from_layer(text, 'morph_analysis', 'morph_analysis_processed', ['normalized_text'])
	manual_morph_proc=remove_attribs_from_layer(text, 'manual_morph', 'manual_morph_processed', ['normalized_text'])
	text.add_layer(flatten(morph_analysis_proc, 'morph_analysis_flat'))
	text.add_layer(flatten(manual_morph_proc, 'manual_morph_flat'))
	diff_tagger.tag(text)
	#for word in text.manual_morph:
	#	print (word)
	print (text.diff_layer.meta)
	print (text.diff_layer)