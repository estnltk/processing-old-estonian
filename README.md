# Workflows for processing 19th century communal court minute books

The repository contains scripts and user dictionaries for processing the Estonian texts written mainly in the second half of 19th century.
As the texts from this period contain a lot of spelling and dialectal variations, tools for analysing contemporary Estonian do not work so well on them.
The parish court records are the main corpora the scripts are tested on.
The first corpus consists of the court records which are manually typed by Tõnis Türna. It can be obtained from https://bitbucket.org/utDigiHum/vallakohtuprotokollid/ 

The second corpus consists of court records entered by the people in the croudsourcing project. It can be obtained from https://bitbucket.org/utDigiHum/ekkd_vallakohtud/

The current repository contains the following files and directories:

## Scripts

This is where the main scripts are.


### annotate_corpus.py

Performs the morphological analysis of municipal court records, saves the results as .tsv files and outputs the statistics and other information to standard output.

The progress of the script is output to stderr.

You can also specify the directory for user dictionaries.

Usage: annotate_corpus.py <input_corpus> <output_directory_for_annotated-files> <optional-user_dictionaries>

The input corpus must be in csv format or in separate xml files.

The csv file must have following headers: id, year, maakond, text. The values have to be separated by '|' character.

The xml-files must have at least following tags: vald, aasta, sisu.

### compare_analyses_tsv.py

Compares the morphological analyses and outputs the first difference it sees.

Can be used mainly when testing a new configurationor a different tagger on the same texts.

Outputs the filename and the line where the difference occured. It also prints 5 lines before and after the difference.

Usage: compare_analyses_tsv.py <directory1> <directory2>

### corpus_readers.py

Contains functions for reading the corpus in csv, xml or tsv format. The functions return the text objects which in addition to the texts contain metadata such as year, location and id.

The id value is mainly for giving the output files of the analysis their unique names.

### evaluate_automatic_morph_analysis.py

Compares the automatic morphological analysis to the manually analyzed corpus. Takes manually_analyzed tsv files as input and directs the statistics into standard output.

You can also specify the location of user dictionary files for automatic morph analysis.

Usage: evaluate_automatic_morph_analysis.py <manually-tagged-files> <optional-user-dictionaries>

### json_csv.py

Converts the user dictionary from json-format to tsv files.

Usage: json_csv.py <json-input-file> <tsv-output-directory>

### make_user_dicts.py

makes user dictionaries from manually morph-analyzed corpus. The files must be in .tsv format.

You can also specify the directory for files containing non-standard estonian words and their normalized forms. The filenames must end with srt and have following structure:

Each line contains the word and its normalized form, which are separated by space. E.G.

om on

mõtsan metsas


Usage: make_user_dictionaries.py <output-directory> <input-directory-with-manual-annotations> <optional-normalized-words>

### morph_eval_utils.py

Contains functions for making the output of diff_layer more readable and human friendly.

### morph_pipeline.py

Contains the functions and default configuration for the morphological analysis pipeline.

## manually_annotated_Türna

The directory consists of manually analyzed and corrected morphological analyses of parish court records from the first corpus (refer to above).

## normalized_wordforms

Contains files with non-standard Estonian wordforms with their normalized counterparts.

## user_dict_Türna

Contains the user dictionaries for analyzing the records from the first corpus (refer to above).