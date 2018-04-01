import sys, os, time, string
import logging, logging.handlers
from optparse import OptionParser
from icontrol.session import iControlRESTSession
from icontrol.exceptions import iControlUnexpectedHTTPError

__author__      = "Angelo Conforti"
__copyright__   = "Copyright 2018, angeloxx@angeloxx.it"

##################################################
# const
##################################################
valid_chars = "-_ %s%s" % (string.ascii_letters, string.digits)

##################################################
# fn
##################################################
def vsToAFM(mgmt,vs):
    if not 'fwEnforcedPolicy' in vs:
        return {}
    try:
        afm = mgmt.get('https://{0}/mgmt/tm/security/firewall/policy/{1}/rules'.format(options.remote,vs["fwEnforcedPolicy"].replace("/","~")))
    except iControlUnexpectedHTTPError as ex:
        print(ex)
        return {}
    
    return(afm.json()['items'])

def decodeRule(rule):
    ret = []
    if "addresses" in rule:
        for item in rule['addresses']:
            ret.append("Address {0}".format(item["name"]))
    if "addressLists" in rule:
        for item in rule['addressLists']:
            ret.append("AddressList {0}".format(item))
    if "geo" in rule:
        for item in rule['geo']:
            ret.append("Geographic Area {0}".format(item["name"]))
    if "portLists" in rule:
        for item in rule['portLists']:
            ret.append("PortList {0}".format(item))
    if "ports" in rule:
        for item in rule['ports']:
            ret.append("Port {0}".format(item['name']))
    if "vlans" in rule:
        for item in rule['vlans']:
            ret.append("VLAN {0}".format(item))

    if rule == {}:
        ret.append("any")
    if rule == {'identity': {}}:
        ret.append("any")
    return ret

def afmToWiki(rules):
    lines = []
    lines.append('{| class="wikitable"')
    lines.append('|-')
    lines.append('! style="width: 250px" | Name')
    lines.append('! style="width: 50px" | Protocol')
    lines.append('! style="width: 250px" | Source')
    lines.append('! style="width: 250px" | Destination')
    lines.append('! style="width: 50px" | Action')
    for rule in rules:
        # Get rule details
        rule["sources"] = []
        rule["destinations"] = []
        #try:
        #    rule['details'] = mgmt.get(rule["selfLink"].replace("localhost",options.remote)).json()
        #except iControlUnexpectedHTTPError as ex:
        #    continue
        if not "ruleList" in rule:
            rule['sources'] = decodeRule(rule['source'])
            rule['destinations'] = decodeRule(rule['destination'])

            rule["sourcesList"] = "<br>".join(rule["sources"])
            rule["destinationsList"] = "<br>".join(rule["destinations"])

            lines.append('|- style="font-size: 90%;"')
            lines.append('| {name}'.format(**rule))
            lines.append('| {ipProtocol}'.format(**rule))
            lines.append('| {sourcesList}'.format(**rule))
            lines.append('| {destinationsList}'.format(**rule))
            lines.append('| {action}'.format(**rule))
        else:
            subrules = mgmt.get('https://{0}/mgmt/tm/security/firewall/rule-list/{1}/rules'.format(options.remote,rule["ruleList"].replace("/","~")))
            for subrule in subrules.json()["items"]:
            
                subrule['name'] = "RuleList {0} <br> {1}".format(rule['name'].replace("_","/"),subrule['name'])
                subrule['sources'] = decodeRule(subrule["source"])
                subrule['destinations'] = decodeRule(subrule["destination"])
                
                subrule["sourcesList"] = "<br>".join(subrule["sources"])
                subrule["destinationsList"] = "<br>".join(subrule["destinations"])

                lines.append('|- style="font-size: 90%;"')
                lines.append('| {name}'.format(**subrule))
                lines.append('| {ipProtocol}'.format(**subrule))
                lines.append('| {sourcesList}'.format(**subrule))
                lines.append('| {destinationsList}'.format(**subrule))
                lines.append('| {action}'.format(**subrule))

    lines.append('|}')
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
parser.add_option("-u", "--username", dest="username", default="api")
parser.add_option("-p", "--password", dest="password", default="apiapi")
parser.add_option("-r", "--remote", dest="remote", default="127.0.0.1")
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

# Connect to the BigIP
try:
    mgmt = iControlRESTSession(options.username, options.password)
    pass
except Exception as e:
    log.error("Unable to login to {0} with '{1}' username (user should be operator or administrator)".format(options.remote, options.username))
    log.error("Error is: {0}".format(e))
    sys.exit(1)

lineno = 0
output = []
for line in specfile.split("\n"):
    lineno=lineno+1
    if line.startswith("#"):
        continue

    values = dict(item.split(":") for item in line.split(";"))
    if not "name" in values:
        log.error("Line {0}, name property not found.. skipped".format(lineno))
        continue
    if not "exporttype" in values:
        log.error("Line {0}, exporttype property not found.. skipped".format(lineno))
        continue
    if not "title" in values:
        log.error("Line {0}, description property not found.. skipped".format(lineno))
        continue
    if not "description" in values:
        values["description"] = ""

    try:
        vs = mgmt.get('https://{0}/mgmt/tm/ltm/virtual/{1}'.format(options.remote,values["name"].replace("/","~")))
    except iControlUnexpectedHTTPError as ex:
        if '404' in ex.__str__():
            log.error("Line {0}, unable to find vs '{1}'.. skipped".format(lineno, values["name"]))
        else:
            log.error("Line {0}, generic error with vs '{1}'.. skipped".format(lineno, values["name"]))
            log.error("Error is: {0}".format(e))
        continue
    except Exception as e:
        log.error("Line {0}, generic error with vs '{1}'.. skipped".format(lineno, values["name"]))
        log.error("Error is: {0}".format(e))
        continue

    log.info("Line {0}, vs found".format(lineno))

    if values["exporttype"] == 'AFM':
        data = vsToAFM(mgmt,vs.json())
        if data != {}:
            output.append({
                "title": values["title"],
                "body": "{0}\n{1}".format(values["description"], afmToWiki(data)),
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
