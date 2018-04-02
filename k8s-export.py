import sys, os, time, string
from kubernetes import client, config
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
    
def deploymentToWiki(items):
    lines = []

    lines.append('{| class="wikitable"')
    lines.append('|- style="vertical-align:top;')
    lines.append('! style="width: 250px" | Name')
    lines.append('! style="width: 50px" | Configured')
    lines.append('! style="width: 50px" | Ready')
    lines.append('! style="width: 50px" | Updated')
    lines.append('! style="width: 400px" | Annotations')

    for item in items:
        lines.append('|- style="font-size: 90%;"')
        lines.append('| {}'.format(item.metadata.name))
        lines.append('| {}'.format(int(item.spec.replicas or 0)))
        lines.append('| {}'.format(int(item.status.available_replicas or 0)))
        lines.append('| {}'.format(int(item.status.updated_replicas or 0)))
        
        annot = []
        for annotation in item.metadata.annotations:
            if annotation.startswith("kubectl.kubernetes.io/"):
                continue
            annot.append("{0}: {1}<br>".format(annotation,item.metadata.annotations[annotation]))

        lines.append('| {}'.format("\n".join(annot)))    

    lines.append('|}')
    print (lines)
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
parser.add_option("-c", "--credential", dest="credential", default="/etc/kubernetes/admin.conf")
parser.add_option("--specfile", dest="specfile", default="")
parser.add_option("--outfile", dest="outfile", default="/tmp/outfile")
parser.add_option("--outmode", dest="outmode", type="choice", choices=['file', 'multifile', 'mail',], default="file")
parser.add_option("--format", dest="format", type="choice", choices=['wiki',], default="wiki")
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

if not os.path.isfile(options.credential):
    log.error("The specified {0} credential file does not exist".format(options.credential))
    sys.exit(1)

if options.outfile == "":
    log.error("Please specify a valid out file with --outfile outfilename parameter")
    sys.exit(1)

log.info("Starting with {0} credentials using {1}".format(options.credential,options.specfile))

# Read the input file
specfile = open(options.specfile).read()

# Connect to the K8S Server
try:
    config.load_kube_config(config_file=options.credential)
    #mgmt = client.CoreV1Api()
    mgmt = client.AppsV1Api()
except Exception as e:
    log.error("Unable to login")
    log.error("Error is: {0}".format(e))
    sys.exit(1)

lineno = 0
output = []
for line in specfile.split("\n"):
    lineno=lineno+1
    if line.startswith("#"):
        continue

    values = dict(item.split(":") for item in line.split(";"))
    if not "namespace" in values:
        log.error("Line {0}, namespace property not found.. skipped".format(lineno))
        continue
    if not "title" in values:
        log.error("Line {0}, title property not found.. skipped".format(lineno))
        continue
    if not "type" in values:
        log.error("Line {0}, type property not found.. skipped".format(lineno))
        continue
    else:
        if not values["type"] in ["pods","deployments","statefulset","allsets"]:
            log.error("Line {0}, type property not valid.. skipped".format(lineno))
            continue
    if not "description" in values:
        values["description"] = ""


    #results = mgmt.list_pod_for_all_namespaces(watch=False)
    if values["type"] == "pods":
        #results = mgmt.list_namespaced_pod(values["namespace"])
        pass

    if values["type"] == "deployments" or values["type"] == "allsets":
        results = mgmt.list_namespaced_deployment(values["namespace"])
        if len(results.items) == 0:
            log.error("Namespace {0}, does not exist.. skipped".format(values["namespace"]))
            continue

        log.info("Namespace {0} contains {1} deployments".format(values["namespace"],len(results.items)))
        output.append({
            "title": values["title"],
            "body": "{0}\n{1}".format(values["description"], deploymentToWiki(results.items)),
            "footer": '{{{{note}}}}Last update {0}'.format(time.ctime())
        })

    if values["type"] == "statefulset" or values["type"] == "allsets":
        results = mgmt.list_namespaced_deployment(values["namespace"])
        if len(results.items) == 0:
            log.error("Namespace {0}, does not exist.. skipped".format(values["namespace"]))
            continue

        log.info("Namespace {0} contains {1} deployments".format(values["namespace"],len(results.items)))
        output.append({
            "title": values["title"],
            "body": "{0}\n{1}".format(values["description"], deploymentToWiki(results.items)),
            "footer": '{{{{note}}}}Last update {0}'.format(time.ctime())
        })


    # output.append({
    #     "title": values["title"],
    #     "body": "{0}\n{1}".format(values["description"], groupToWiki(data)),
    #     "footer": '{{{{note}}}}Last update {0}'.format(time.ctime())
    # })


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
