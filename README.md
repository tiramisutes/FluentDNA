﻿# DNA Data Visualization (DDV) software

This application creates visualizations of FASTA formatted DNA nucleotide data.
DDV generates a DeepZoomImage visualizations similar to Google Maps for FASTA files.

## DDV 2.0 Features

DDV 2.0 is a complete rewrite in Python of DDV.  DDV 2.0 has a much expanded feature set for handling
large, multipart files.  It can put an entire genome on a single image, marked with contig names.
DDV 2.0 has features in development for exploring genome alignments, annotations, and transposon alignments.
It was developed by Newline Technical Innovations and can be found at:
https://github.com/josiahseaman/DDV/tree/python-master

## DDV 1.1
This project is a fork of the C# DDV developed at Concordia University.
https://github.com/photomedia/DDV/

DDV Licence:
https://github.com/photomedia/DDV/blob/master/DDV-license.txt

### Examples (Demonstration):

http://www.photomedia.ca/DDV/

Visualizations generated with DDV can be placed on a web server. 
The following contains the links to examples of the visualizations 
generated by Tomasz Neugebauer, Éric Bordeleau, Vincent Burrus and Ryszard Brzezinski 
with this software: DNA Data Visualizations Generated with DDV Software. 
These examples include a number of bacteria chromosomes, as well as the entire Homo Sapiens genome. 


## Compile Instructions
Only necessary for developers intending to make new deployable binary files:

- Using the new python, install all the requirements `/path/to/projects/ddv_python/bin/pip install -r /path/to/DDV/Requirements.txt`
- `/path/to/projects/ddv_python/bin/pip install hg+https://bitbucket.org/BryanHurst/cx_freeze`
- If the above install fails, then there is a problem with your python shared libraries, I have a clone of the cx_freeze repo with a temp fix
- CD to a directory where you want to download it, then `hg clone hg+https://bitbucket.org/BryanHurst/cx_freeze; cd cx_freeze; /path/to/projects/adsm_python/bin/python setup.py install`
