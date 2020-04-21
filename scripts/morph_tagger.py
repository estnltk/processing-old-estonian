from estnltk import Text
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


def morph_tagger(text, conf):
	#Initialize the configuration
	#If alphabet corrections should be performed
	if 'prenormalize' not in conf:
		conf['prenormalize']=True
	if 'add_punctuation_analyses' not in conf:
		conf['add_punctuation_analyses'] = True
	#If user dictionary should be used
	if 'use_user_dictionary' not in conf:
		conf['use_user_dictionary']=False
	if conf['use_user_dictionary']:
		if 'userdict' not in conf:
			conf['userdict']=UserDictTagger(validate_vm_categories=False)
	if 'vm_analyzer' not in conf:
		conf['vm_analyzer'] = VabamorfAnalyzer(guess=False, propername=False)
	if 'newline_sentence_tokenizer' not in conf:
		conf['newline_sentence_tokenizer'] = SentenceTokenizer( base_sentence_tokenizer=LineTokenizer() )
	if 'tokens_tagger' not in conf:
		conf['tokens_tagger'] = TokensTagger()
	if conf['prenormalize'] and 'prenormalizer' not in conf:
		conf['prenormalizer']=word_prenormalizer()
	global add_punctuation_analyses
	#For testing the pretokenized functions
	txt=text.text
	multiword_expressions = []
	raw_words = txt.split(' ')
	for raw_word in raw_words:
		if ' ' in raw_word:
			multiword_expressions.append(raw_token)
	#text_str = ' '.join(raw_words)
	#meta=text.meta
	#text=Text(text_str)
	#text.meta=meta
	conf['tokens_tagger'].tag(text)
	multiword_expressions = [mw.split() for mw in multiword_expressions]
	compound_tokens_tagger = PretokenizedTextCompoundTokensTagger( multiword_units = multiword_expressions )
	compound_tokens_tagger.tag(text)
	#CompoundTokenTagger(tag_initials = False).tag(text)
	#text.tag_layer(['sentences'])
	text.tag_layer(['words'])
	conf['newline_sentence_tokenizer'].tag(text)
	if conf['prenormalize']:
		conf['prenormalizer'].retag(text)
	conf['vm_analyzer'].tag(text)
	# Perform the fixes
	if conf['use_user_dictionary']:
		user_dict_location_file=os.path.join(conf['user_dict_path'], text.meta['location']+".tsv")
		user_dict_global_file=os.path.join(conf['user_dict_dir'], 'global.tsv')
		if os.path.exists(user_dict_location_file):
			conf['userdict'].add_words_from_csv_file(user_dict_location_file, encoding='utf-8', delimiter='\t')
		if os.path.exists(user_dict_global_file):
			conf['userdict'].add_words_from_csv_file(user_dict_global_file, encoding='utf-8', delimiter='\t')
		conf['userdict'].retag(text)
	if conf['add_punctuation_analyses']:
		add_punctuation_analysis( text )
	return text



