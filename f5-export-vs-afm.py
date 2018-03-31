import sys, os, mwclient
import logging, logging.handlers
from optparse import OptionParser
from f5.bigip import ManagementRoot
from icontrol.exceptions import iControlUnexpectedHTTPError

__author__      = "Angelo Conforti"
__copyright__   = "Copyright 2018, angeloxx@angeloxx.it"

##################################################
# fnt
##################################################
def vsToAFM(mgmt,vs):
    if not 'fwEnforcedPolicy' in vs.raw:
        return {}

    #mgmt.tm.asm.policies_s.policy.load(id=p_object.id)
    #afm = mgmt.tm.security.firewall.policy_s.get_collection(name=vs.raw['fwEnforcedPolicy'])
    #afm = mgmt.tm.security.firewall.policy_s.get_collection()[0]
    #afm = [element for element in mgmt.tm.security.firewall.policy_s.get_collection() if element.raw['name']==vs.raw['fwEnforcedPolicy']]
    afms = list(filter(lambda x: x.raw["fullPath"] == vs.raw['fwEnforcedPolicy'], mgmt.tm.security.firewall.policy_s.get_collection()))
    if len(afms) == 0:
        return {}
    else:
        afm = afms.pop()
    #print (afm.rules_s.rule.)
    #print (afm.rules_s.rule.load(name=""))

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
parser.add_option("-r", "--remote", dest="remote", default="172.18.122.21")
parser.add_option("--specfile", dest="specfile", default="")
parser.add_option("--outfile", dest="outfile", default="/tmp/outfile")
parser.add_option("--outmode", dest="outmode", default="file")
parser.add_option("--format", dest="format", type="choice", choices=['wiki', 'yaml', 'mail',], default="wiki")
parser.add_option("--mailserver", dest="mailserver", default="mail")
parser.add_option("--rcpt", dest="rcpt", default="")
parser.add_option("--from", dest="from", default="")
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
    mgmt = ManagementRoot(options.remote, options.username, options.password)
    pass
except Exception as e:
    log.error("Unable to login to {0} with '{1}' username (user should be operator or administrator)".format(options.remote, options.username))
    log.error("Error is: {0}".format(e))
    sys.exit(1)

lineno = 0
for line in specfile.split("\n"):
    lineno=lineno+1
    if line.startswith("#"):
        continue

    values = dict(item.split("=") for item in line.split(","))
    if not "name" in values:
        log.error("Line {0}, name property not found.. skipped".format(lineno))
        continue
    if not "exporttype" in values:
        log.error("Line {0}, exporttype property not found.. skipped".format(lineno))
        continue
    if not "description" in values:
        log.error("Line {0}, description property not found.. skipped".format(lineno))
        continue

    try:
        vs = mgmt.tm.ltm.virtuals.virtual.load(name=values["name"])
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
        data = vsToAFM(mgmt,vs)
