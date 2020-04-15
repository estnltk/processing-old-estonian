# ===========================================================
#    Utilities for getting annotation alignments from 
#    DiffTagger's morphological analysis comparison 
#    results
#
#    Originally developed for:
#      https://github.com/estnltk/eval_experiments_lrec_2020/
#      https://github.com/estnltk/eval_experiments_lrec_2020/blob/master/scripts_and_data/morph_eval_utils.py
#    Author:
#      Siim Orasmaa
# ===========================================================

from estnltk.text import Text
from estnltk.taggers.standard_taggers.diff_tagger import iterate_diff_conflicts
from estnltk.taggers.standard_taggers.diff_tagger import iterate_modified

from collections import defaultdict

def get_estnltk_morph_analysis_diff_annotations( text_obj, layer_a, layer_b, diff_layer ):
    ''' Collects differing sets of annotations from EstNLTK's morph_analysis diff_layer. 
        Groups differences by word spans. Returns a list of dicts.
    '''
    STATUS_ATTR = '__status'
    assert isinstance(text_obj, Text)
    assert layer_a in text_obj.layers, '(!) Layer {!r} missing from: {!r}'.format(layer_a, text_obj.layers.keys())
    assert layer_b in text_obj.layers, '(!) Layer {!r} missing from: {!r}'.format(layer_b, text_obj.layers.keys())
    assert diff_layer in text_obj.layers, '(!) Layer {!r} missing from: {!r}'.format(diff_layer, text_obj.layers.keys())
    layer_a_spans = text_obj[layer_a]
    layer_b_spans = text_obj[layer_b]
    common_attribs = set(text_obj[layer_a].attributes).intersection( set(text_obj[layer_b].attributes) )
    assert len(common_attribs) > 0, '(!) Layers {!r} and {!r} have no common attributes!'.format(layer_a, layer_b)
    assert STATUS_ATTR not in common_attribs, "(!) Unexpected attribute {!r} in {!r}.".format(STATUS_ATTR, common_attribs)
    assert layer_a not in ['start', 'end']
    assert layer_b not in ['start', 'end']
    collected_diffs = []
    missing_annotations = 0
    extra_annotations   = 0
    a_id = 0
    b_id = 0
    for diff_span in iterate_modified( text_obj[diff_layer], 'span_status' ):
        ds_start = diff_span.start
        ds_end =   diff_span.end
        # Find corresponding span in both layer
        a_span = None
        b_span = None
        while a_id < len(layer_a_spans):
            cur_a_span = layer_a_spans[a_id]
            if cur_a_span.start == ds_start and cur_a_span.end == ds_end:
                a_span = cur_a_span
                break
            a_id += 1
        while b_id < len(layer_b_spans):
            cur_b_span = layer_b_spans[b_id]
            if cur_b_span.start == ds_start and cur_b_span.end == ds_end:
                b_span = cur_b_span
                break
            b_id += 1
        if a_span == None:
            raise Exception('(!) {!r} not found from layer {!r}'.format(diff_span, layer_a))
        if b_span == None:
            raise Exception('(!) {!r} not found from layer {!r}'.format(diff_span, layer_b))
        a_annotations = []
        for a_anno in a_span.annotations:
            a_dict = a_anno.__dict__.copy()
            a_dict = {a:a_dict[a] for a in a_dict.keys() if a in common_attribs}
            a_dict[STATUS_ATTR] = None
            a_annotations.append( a_dict )
        b_annotations = []
        for b_anno in b_span.annotations:
            b_dict = b_anno.__dict__.copy()
            b_dict = {b:b_dict[b] for b in b_dict.keys() if b in common_attribs}
            b_dict[STATUS_ATTR] = None
            b_annotations.append( b_dict )
        for a_anno in a_annotations:
            match_found = False
            for b_anno in b_annotations:
                if a_anno == b_anno:
                    a_anno[STATUS_ATTR] = 'COMMON'
                    b_anno[STATUS_ATTR] = 'COMMON'
                    match_found = True
                    break
            if not match_found:
                missing_annotations += 1
                a_anno[STATUS_ATTR] = 'MISSING'
        for b_anno in b_annotations:
            if b_anno not in a_annotations:
                extra_annotations += 1
                b_anno[STATUS_ATTR] = 'EXTRA'
        collected_diffs.append( {'text':diff_span.text, layer_a: a_annotations, layer_b: b_annotations, 'start':diff_span.start, 'end':diff_span.end} )
    # Sanity check: missing vs extra annotations:
    # Note: text_obj[diff_layer].meta contains more *_annotations items, because it also 
    #       counts annotations in missing spans and extra spans; Unfortunately, merely
    #       subtracting:
    #                       missing_annotations - missing_spans
    #                       extra_annotations - extra_spans
    #       does not work either, because one missing or extra span may contain more 
    #       than one annotation. So, we have to re-count extra and missing annotations ...
    normalized_extra_annotations   = 0
    normalized_missing_annotations = 0
    for span in text_obj[diff_layer]:
        for status in span.span_status:
            if status == 'missing':
                normalized_missing_annotations += 1
            elif status == 'extra':
                normalized_extra_annotations += 1
    if missing_annotations != text_obj[diff_layer].meta['missing_annotations'] - normalized_missing_annotations:
        nr_a = missing_annotations
        nr_b = text_obj[diff_layer].meta['missing_annotations'] - normalized_missing_annotations
        msg = 'Please check that input layer names layer_a and layer_b appear in the same order as in the DiffTagger.'
        raise ValueError('(!) Mismatching numbers of missing annotations {} vs {}.\n{}'.format(nr_a, nr_b, msg))
    if extra_annotations != text_obj[diff_layer].meta['extra_annotations'] - normalized_extra_annotations:
        nr_a = extra_annotations
        nr_b = text_obj[diff_layer].meta['extra_annotations'] - normalized_extra_annotations
        msg = 'Please check that input layer names layer_a and layer_b appear in the same order as in the DiffTagger.'
        raise ValueError('(!) Mismatching numbers of extra annotations {} vs {}.\n{}'.format(nr_a, nr_b, msg))
    return collected_diffs


def get_estnltk_morph_analysis_annotation_alignments( collected_diffs, layer_names, focus_attributes=['root','partofspeech', 'form'], remove_status=True ):
    ''' Calculates annotation alignments between annotations in collected_diffs. 
        For each word span, determines common, modified, extra and missing annotations.
        Returns a list of alignment dicts.
    '''
    assert isinstance(layer_names, list) and len(layer_names) == 2
    STATUS_ATTR = '__status'
    MATCHING_ATTR    = '__matching'
    MISMATCHING_ATTR = '__mismatching'
    alignments  = []
    annotations_by_layer = defaultdict(int)
    if len(collected_diffs) > 0:
        first_diff = collected_diffs[0]
        all_attributes = []
        for key in first_diff.keys():
            if key not in ['text', 'start', 'end']:
                all_attributes = [k for k in first_diff[key][0].keys() if k != STATUS_ATTR]
                assert key in layer_names
        assert len( all_attributes ) > 0
        assert len([a for a in focus_attributes if a in all_attributes]) == len(focus_attributes)
        for word_diff in collected_diffs:
            alignment = word_diff.copy()
            a_anns = word_diff[layer_names[0]]
            b_anns = word_diff[layer_names[1]]
            annotations_by_layer[layer_names[0]] += len(a_anns)
            annotations_by_layer[layer_names[1]] += len(b_anns)
            alignment['alignments'] = []
            del alignment[layer_names[0]]
            del alignment[layer_names[1]]
            a_used = set()
            b_used = set()
            for a_id, a in enumerate(a_anns):
                # Find fully matching annotation
                for b_id, b in enumerate(b_anns):
                    if a == b:
                        al = {STATUS_ATTR:'COMMON', layer_names[0]:a, layer_names[1]:b }
                        al[MISMATCHING_ATTR] = []
                        al[MATCHING_ATTR] = all_attributes.copy()
                        alignment['alignments'].append( al )
                        a_used.add(a_id)
                        b_used.add(b_id)
                        break
                if a_id in a_used:
                    continue
                # Find partially matching annotation
                closest_b = None
                closest_b_id = None
                closest_common   = []
                closest_uncommon = []
                for b_id, b in enumerate(b_anns):
                    if a_id in a_used or b_id in b_used:
                        continue
                    if b[STATUS_ATTR] == 'COMMON':
                        # Skip b that has been previously found as being common
                        continue
                    if a != b:
                        #count common attribs
                        matching_attribs = []
                        mismatching = []
                        for attr in all_attributes:
                            if a[attr] == b[attr]:
                                matching_attribs.append(attr)
                            else:
                                mismatching.append(attr)
                        if len(matching_attribs) > len(closest_common):
                            focus_1 = []
                            focus_2 = []
                            if closest_b != None:
                                focus_1 = [a for a in focus_attributes if a in matching_attribs]
                                focus_2 = [a for a in focus_attributes if a in closest_common]
                            # in case of a tie, prefer matches with more focus attributes
                            if len(focus_1) == len(focus_2) or len(focus_1) > len(focus_2):
                                closest_common   = matching_attribs
                                closest_uncommon = mismatching
                                closest_b_id = b_id
                                closest_b = b
                if closest_b != None:
                    al = {STATUS_ATTR:'MODIFIED', layer_names[0]:a, layer_names[1]:closest_b }
                    al[MISMATCHING_ATTR] = closest_uncommon
                    al[MATCHING_ATTR] = closest_common
                    alignment['alignments'].append( al )
                    a_used.add(a_id)
                    b_used.add(closest_b_id)
                else:
                    al = {STATUS_ATTR:'MISSING', layer_names[0]:a, layer_names[1]:{} }
                    al[MISMATCHING_ATTR] = all_attributes.copy()
                    al[MATCHING_ATTR] = []
                    alignment['alignments'].append( al )
                    a_used.add(a_id)
            for b_id, b in enumerate(b_anns):
                if b_id not in b_used:
                    al = {STATUS_ATTR:'EXTRA', layer_names[0]:{}, layer_names[1]:b }
                    al[MISMATCHING_ATTR] = all_attributes.copy()
                    al[MATCHING_ATTR] = []
                    alignment['alignments'].append( al )
            alignments.append( alignment )
    # Sanity check: check that we haven't lost any annotations during the careful alignment
    annotations_by_layer_2 = defaultdict(int)
    for word_diff in alignments:
        for al in word_diff['alignments']:
            for layer in layer_names:
                if len(al[layer].keys()) > 0:
                    annotations_by_layer_2[layer] += 1
    for layer in layer_names:
        if annotations_by_layer[layer] != annotations_by_layer_2[layer]:
           # Output information about the context of the failure
            from pprint import pprint
            print('='*50)
            print(layer,'  ',annotations_by_layer[layer], '  ', annotations_by_layer_2[layer])
            print('='*50)
            pprint(collected_diffs)
            print('='*50)
            pprint(alignments)
            print('='*50)
        assert annotations_by_layer[layer] == annotations_by_layer_2[layer], '(!) Failure in annotation conversion.'
    # Remove STATUS_ATTR's from annotations dict's (if required)
    if remove_status:
        for word_diff in alignments:
            for al in word_diff['alignments']:
                for layer in layer_names:
                    if STATUS_ATTR in al[layer].keys():
                        del al[layer][STATUS_ATTR]
    return alignments



def get_concise_morph_diff_alignment_str( alignments, layer_a, layer_b, focus_attributes=['root','partofspeech','form'], return_list=False ):
    ''' Formats differences of morph analysis annotations as a string (or a list of strings).'''
    STATUS_ATTR = '__status'
    MATCHING_ATTR    = '__matching'
    MISMATCHING_ATTR = '__mismatching'
    out_str = []
    max_len = max(len(layer_a), len(layer_b))
    max_label_len = max( [len(a) for a in ['MODIFIED', 'MISSING', 'EXTRA', 'COMMON']])
    for alignment in alignments:
        assert STATUS_ATTR      in alignment.keys()
        assert MATCHING_ATTR    in alignment.keys()
        assert MISMATCHING_ATTR in alignment.keys()
        assert layer_a in alignment.keys()
        assert layer_b in alignment.keys()
        if alignment[STATUS_ATTR] == 'MODIFIED':
            focus_is_matching = len([fa for fa in focus_attributes if fa in alignment[MATCHING_ATTR]]) == len(focus_attributes)
            if not focus_is_matching:
                a = [alignment[layer_a][fa] for fa in focus_attributes]
                b = [alignment[layer_b][fa] for fa in focus_attributes]
                mod_attr = [m_attr for m_attr in alignment[MISMATCHING_ATTR] if m_attr in focus_attributes]
                out_str.append( ('{:'+str(max_len)+'}     {}').format(alignment[STATUS_ATTR], mod_attr) )
                out_str.append((' {:'+str(max_len)+'}   ').format(layer_a) + ' '+str(a))
                out_str.append((' {:'+str(max_len)+'}   ').format(layer_b) + ' '+str(b))
            else:
                a = [alignment[layer_a][fa] for fa in focus_attributes+alignment[MISMATCHING_ATTR]]
                b = [alignment[layer_b][fa] for fa in focus_attributes+alignment[MISMATCHING_ATTR]]
                out_str.append( ('{:'+str(max_label_len)+'}').format(alignment[STATUS_ATTR]) )
                out_str.append((' {:'+str(max_len)+'}   ').format(layer_a) + ' '+str(a))
                out_str.append((' {:'+str(max_len)+'}   ').format(layer_b) + ' '+str(b))
        elif alignment[STATUS_ATTR] == 'COMMON':
            a = [alignment[layer_a][fa] for fa in focus_attributes]
            b = [alignment[layer_b][fa] for fa in focus_attributes]
            out_str.append( ('{:'+str(max_label_len)+'}').format(alignment[STATUS_ATTR]) )
            out_str.append((' {:'+str(max_len)+'}   ').format(layer_a) + ' '+str(a))
            out_str.append((' {:'+str(max_len)+'}   ').format(layer_b) + ' '+str(b))
        elif alignment[STATUS_ATTR] in ['EXTRA', 'MISSING']:
            a = [alignment[layer_a][fa] for fa in focus_attributes] if len(alignment[layer_a].keys()) > 0 else []
            b = [alignment[layer_b][fa] for fa in focus_attributes] if len(alignment[layer_b].keys()) > 0 else []
            out_str.append( ('{:'+str(max_label_len)+'}').format(alignment[STATUS_ATTR]) )
            if a:
                out_str.append((' {:'+str(max_len)+'}   ').format(layer_a) + ' '+str(a))
            if b:
                out_str.append((' {:'+str(max_len)+'}   ').format(layer_b) + ' '+str(b))
        else:
            raise Exception( '(!) unexpected __status: {!r}'.format(alignment[STATUS_ATTR]) )
    return '\n'.join( out_str ) if not return_list else out_str

