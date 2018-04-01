import sys, os, mwclient, glob
import logging, logging.handlers
from optparse import OptionParser

__author__      = "Angelo Conforti"
__copyright__   = "Copyright 2018, angeloxx@angeloxx.it"

##################################################
# Configure logger
##################################################
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
handlerSyslog = logging.handlers.SysLogHandler(address = '/dev/log')
formatterSyslog = logging.Formatter('%(module)s[%(process)s]: %(levelname)s - %(message)s')
handlerSyslog.setFormatter(formatterSyslog)
log.addHandler(handlerSyslog)

##################################################
# Configure optionparser
##################################################
parser = OptionParser()
parser.add_option("-u", "--username", dest="username", default="")
parser.add_option("-p", "--password", dest="password", default="")
parser.add_option("-r", "--remote", dest="remote", default="www.mediawiki.org")
parser.add_option("--page", dest="page", default="Project:Sandbox")
parser.add_option("--section", dest="section", default="")
parser.add_option("--proto", dest="proto", default="https")
parser.add_option("--content", dest="content_file", default="")
parser.add_option("--summary", dest="summary", default="Bot: Automatically edited by mini-mw-editor")
parser.add_option("--minor", dest="is_minor", default=False, action="store_true")
parser.add_option("--subpages", dest="subpages", default=False, action="store_true")
(options, args) = parser.parse_args()

if options.subpages:
    subpagefiles = glob.glob("{0}-*".format(options.content_file))
    if not subpagefiles:
        log.error("Please specify a valid content basename with --content=filename parameter")
        sys.exit(1)    
    if options.section != "":
        log.error("The --section and --subpages options are incompatible")
        sys.exit(1)    
else:
    if options.content_file == "":
        log.error("Please specify a valid content file with --content=filename parameter")
        sys.exit(1)    
    if not os.path.isfile(options.content_file):
        log.error("The specified {0} file does not exist".format(options.content_file))
        sys.exit(1)    
        
    

if options.page == "":
    log.error("Please specify a valid page file with --page='pagename' parameter")
    sys.exit(1)       


log.info("Edit page {0} in {1} using {2}".format(options.remote,options.page,options.content_file))

##################################################
# Connect, edit, exit!
##################################################
try:
    if options.username == "":
        site = mwclient.Site(options.remote, force_login=False)
        log.info("Connected to remote server (as anonymous user)")
    else:
        site = mwclient.Site(options.remote)
        site.login(options.username, options.password)
        log.info("Connected to remote server (as {0})".format(options.username))
except Exception as e: 
    log.error("Unable to connect, abort")
    log.error("Error is: {0}".format(e))
    sys.exit(1)

try:
    if options.section == "":
        if options.subpages:
            mainpage = []

            # Create subpages
            for subpagefile in subpagefiles:
                title = subpagefile.replace(options.content_file+"-","")
                mainpage.append("== {0} ==".format(title))
                mainpage.append("{{{{{0}/{1}}}}}".format(options.page,title))
                log.info("Create or edit the {0}/{1} page".format(options.page,title))


                page = site.pages["{0}/{1}".format(options.page,title)]
                text = open(subpagefile).read()
                page.save(text, summary=options.summary, bot=True, minor=options.is_minor)

            # Create the main page
            page = site.pages[options.page]
            log.info("Create or edit the {0} master-page".format(options.page))
            page.save("\n".join(mainpage), summary=options.summary, bot=True, minor=options.is_minor)
        else:
            log.info("Create or edit the {0} page".format(options.page))
            page = site.pages[options.page]
            text = open(options.content_file).read()
            page.save(text, summary=options.summary, bot=True, minor=options.is_minor)
    else:
        log.info("Create or edit the {0} page, section {1}".format(options.page,options.section))
        page = site.pages[options.page]
        text = page.text(section=options.section)
        text = open(options.content_file).read()
        page.save(text, summary=options.summary, bot=True, minor=options.is_minor, section=options.section)
except Exception as e: 
    log.error("Unable to save the page, abort")
    log.error("Error is: {0}".format(e))
    sys.exit(1)

sys.exit(0)
    