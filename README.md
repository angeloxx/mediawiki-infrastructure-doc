# Introduction

The objective of this project is to document the firewall policies and LDAP groups membership in an environment that uses OpenLDAP and BigIP F5. The daily challenge that this project wants to address is to document and update these informations in a enterprise Mediawiki.

# Usage

Create a list of F5's Virtual Server that you want document on your Mediawiki using this format:

    # List the exported vs in <vsname>,exporttype[AFM|VS],description format
    name=/Common/nonexist,exporttype=AFM,title=notexists,description=This VS does not exists
    name=/Common/test,exporttype=AFM,title=test1,description=TEST virtual server
    name=/Common/test,exporttype=AFM,title=test2 prova 123,description=TEST virtual server 2
    exporttype=AFM,title=AFM,description=This VS does not exists

launch the exporter with:

    python3 f5-export-vs-afm.py --specfile f5-export-vs-afm.list --format wiki --outfile f5-export-vs-afm.wiki --remote f5 --username admin --password password

or
    python3 f5-export-vs-afm.py --specfile f5-export-vs-afm.list --format wiki --outfile f5-export-vs-afm.wiki --remote f5 --username admin --password password --outmode multifile

and import the file in mediawiki with:

    python3.5 mini-mw-editor.py  --content f5-export-vs-afm.wiki --remote www.mediawiki.org --page "Project:Sandbox"

or 

    python3.5 mini-mw-editor.py  --content f5-export-vs-afm.wiki --remote www.mediawiki.org --page "Project:Sandbox" --subpages

# Mediawiki
The script creates the main page that contains all exported elements OR a master page that uses Embed feature of Mediawiki to import all created subpages

![Sample](sample.png)