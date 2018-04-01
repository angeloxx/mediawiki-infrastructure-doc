import sys, os, time, string, ldap
from binascii import hexlify
import logging, logging.handlers
from optparse import OptionParser

__author__      = "Angelo Conforti"
__copyright__   = "Copyright 2018, angeloxx@angeloxx.it"

##################################################
# const
##################################################
valid_chars = "-_ %s%s" % (string.ascii_letters, string.digits)
##################################################
# fn
##################################################
    
def groupToWiki(group):
    lines = []
    lines.append('Group {} members:'.format((group["cn"][0]).decode("utf-8")))
    if "memberUid" in group:
        for member in group["memberUid"]:
            lines.append('* memberUid: {}'.format((member).decode("utf-8")))

    if "member" in group:
        for member in group["member"]:
            lines.append('* member: {}'.format((member).decode("utf-8")))

    return "\n".join(lines)


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
parser.add_option("-u", "--binddn", dest="binddn", default="cn=manager,o=domain,o=tld")
parser.add_option("-p", "--password", dest="password", default="apiapi")
parser.add_option("-r", "--remote", dest="remote", default="127.0.0.1")
parser.add_option("--proto", dest="proto", choices=['ldap','ldaps',], default="ldap")
parser.add_option("--specfile", dest="specfile", default="")
parser.add_option("--outfile", dest="outfile", default="/tmp/outfile")
parser.add_option("--outmode", dest="outmode", type="choice", choices=['file', 'multifile', 'mail',], default="file")
parser.add_option("--format", dest="format", type="choice", choices=['wiki',], default="wiki")
parser.add_option("--mailserver", dest="mailserver", default="mail")
parser.add_option("--rcpt", dest="rcpt", default="")
parser.add_option("--from", dest="from", default="")
parser.add_option("--ignore-ssl-error", dest="ignore_ssl_error", default=False, action="store_true")
(options, args) = parser.parse_args()

if options.specfile == "":
    log.error("Please specify a valid spec file with --specfile specfilename parameter")
    sys.exit(1)

if not os.path.isfile(options.specfile):
    log.error("The specified {0} file does not exist".format(options.specfile))
    sys.exit(1)

if options.outfile == "":
    log.error("Please specify a valid out file with --outfile outfilename parameter")
    sys.exit(1)

log.info("Starting with {0} using {1}".format(options.remote,options.specfile))

# Read the input file
specfile = open(options.specfile).read()

# Connect to the LDAP
try:
    mgmt = ldap.initialize('{0}://{1}'.format(options.proto,options.remote),bytes_mode=False)
    mgmt.simple_bind(options.binddn, options.password)
    pass
except Exception as e:
    log.error("Unable to login to {0}://{1} with '{2}' username".format(options.proto, options.remote, options.binddn))
    log.error("Error is: {0}".format(e))
    sys.exit(1)

lineno = 0
output = []
for line in specfile.split("\n"):
    lineno=lineno+1
    if line.startswith("#"):
        continue

    values = dict(item.split(":") for item in line.split(";"))
    if not "dn" in values:
        log.error("Line {0}, dn property not found.. skipped".format(lineno))
        continue
    if not "title" in values:
        log.error("Line {0}, description property not found.. skipped".format(lineno))
        continue
    if not "description" in values:
        values["description"] = ""


    results = mgmt.search_s(values["dn"], ldap.SCOPE_BASE)
    if len(results) == 1:
        data = results[0][1]
        output.append({
            "title": values["title"],
            "body": "{0}\n{1}".format(values["description"], groupToWiki(data)),
            "footer": '{{{{note}}}}Last update {0}'.format(time.ctime())
        })


if options.outmode == "file":
    with open(options.outfile, 'w') as the_file:
        for line in output:
            the_file.write('== {} =='.format(line["title"])  + "\n")
            the_file.write(line["body"] + "\n")
            the_file.write(line["footer"] + "\n")
if options.outmode == "multifile":
    for single in output:
        # Sanitize subpage name
        filetitle = ''.join(c for c in single["title"] if c in valid_chars)
        filetitle = filetitle.replace(' ','_') # I don't like spaces in filenames.        
        with open("{0}-{1}".format(options.outfile, filetitle), 'w') as the_file:
            the_file.write(single["body"] + "\n")
            the_file.write("<br>" + single["footer"] + "\n")
