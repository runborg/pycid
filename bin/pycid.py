from pprint import pprint
import pycid
import os
import IPython
from string import Template
from ConfigParser import ConfigParser
from pycid import workflow,mfnmatch
from Exscript.Queue import Queue
from Exscript.Account import Account
from Exscript.Host import Host
from Exscript.util.decorator import bind
from Exscript.util.log import log_to_file, log_to
from Exscript.FileLogger import FileLogger
from Exscript.Logger import Logger
from optparse import OptionParser
import thread
import json
import sys
from time import sleep
mutex = thread.allocate_lock()
config = None
basedir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
opts = None

config_groups = {}



def excallback(job, result):
  global config_groups
  mutex.acquire()
  if opts.verbose > 1: print job
  #try:results[job[0]] = result
  #except: pass
  try:config_groups[job[0]]['devices'][job[1]]['result'] = result
  except: pass
  mutex.release() 



def load_config():
  #Loads a configurationfile into memory
  global config,config_groups,basedir
  config_file = os.path.join(basedir,"etc","pycid.conf")
  config  = ConfigParser()
  config.read(config_file)
  

def load_options():
  global opts
  parser = OptionParser()
  parser.add_option("-t","--threads", dest="threads",help="Number of threads to run", type="int")
  parser.add_option("-g","--group", dest="group", help="Spesify groups to run, comma separated (NOT IMPLEMENTED)")
  parser.add_option("-d","--device", dest="device", help="Name of devices to run, comma separated (NOT IMPLEMENTED)")
  parser.add_option("--debug", dest="verbose", action="store_const", const=2, help="Enable full debugging, its also smart to use --threads 1 (NOT IMPLEMENTED)")
  parser.add_option("--verbose", dest="verbose", action="store_const", const=1, help="Enable verbose output")
  parser.add_option("--ipyshell", dest="ipyshell", action="store_true", help="Enable IPython shell before exiting")
  parser.add_option("-q", "--quiet", dest="quiet", action="store_true", help="Redirect stderr from devices to devnull")
  (opts, args) = parser.parse_args()
  

def git(cmd, arg, repoDir):
  cmd = ['git', cmd, arg]
  p = subprocess.Popen(cmd, cwd=repoDir)
  p.wait()


def main():
  global config, opts
  """
  Main runtime routine
  """
  load_config()
  load_options()
  #Read system configuration from file
  groups = config.get("system", "groups")
  if opts.quiet: sys.stderr = open(os.devnull,'w')

  for group in groups.split():
    if opts.verbose > 0: print "Group %s found" % group
    section = "_%s" % group
    
    g = {}
    if config.has_option(section,"name"):  g["_name"] = config.get(section,         "name", group)
    else:                                  g["_name"] = config.get("group_default", "name", group)
    
    if config.has_option(section, "devfile"): g["devfile"] = config.get(section,         "devfile")
    else:                                     g["devfile"] = config.get("group_default", "devfile")
    
    if config.has_option(section, "filename"): g["filename"] = config.get(section, "filename")
    else:                                      g["filename"] = config.get("group_default", "filename")

    g['name']     = Template(g["_name"]).safe_substitute({'group': group})
    #g['filename'] = Template(g["_filename"]).safe_substitute({'group': group,   'name': 'testfilename' ,    'address': '127.0.0.1'})
    g['git_dir']  = os.path.join(os.path.realpath(config.get("system", "gitrepo")), g["name"])
    g['routerdb'] = os.path.join(os.path.realpath(config.get("system", "gitrepo")), g["name"], g['devfile'])

    if config.has_option(section, "loginrc"): g["_loginrc"] = config.get(section, "loginrc")
    else:                                     g["_loginrc"] = config.get("group_default", "loginrc")
           
            
    g['loginrc'] = os.path.realpath(Template(g["_loginrc"]).safe_substitute({'basedir': basedir, 'group': group}))
    if opts.group:  # IF parameter group spesified, only run on devices in that group
      if not mfnmatch.longest(group,opts.group.split(',')) and not mfnmatch.longest(g['name'],opts.group.split(',')): continue
    config_groups[group] = g



    #Reading router.db file for all groups
  for _g in config_groups:
      g = config_groups[_g]
      config_groups[_g]['devices'] = {}
      devices = {}

 #     print "%s : %s" % (_g, g)

      if not os.path.isfile(g['routerdb']):
        sys.stderr.write("ERROR: device database for group %s not found\n" % _g)
        continue

      # Load LoginRC file for group
      try:
        loginrc = pycid.loginrc(g['loginrc'])
        #print loginrc.get_all()
      except Exception as e:
        sys.stderr.write("ERROR: Unable to load loginrc for group %s (%s)\n" % (_g, e))
        continue        
      with open(g['routerdb'],'r') as f:
        for l in f.readlines():
          dev = {}
          line = l.strip()
          if not line.startswith("#") and line:
            e = line.split(";")
            try:
              if not e[2] in pycid.workflow.driver_map: sys.stderr.write("ERROR: workflow %s not found on node %s:%s\n" % (e[2], _g, e[0])); continue
              if opts.device: # IF parameter "--device" spesified, only run on device with matching name
                if not mfnmatch.longest(e[0],opts.device.split(',')): continue
              dev['name'] = e[0]
              dev['host'] = Host(e[1])
              dev['workflow_name'] = e[2]
              #dev['workflow'] = pycid.workflow.Workflow(pycid.workflow.driver_map[e[2]])
	      opt = e[3] if e[3].startswith('{') else "{%s}" % e[3]
	      #print opt
              dev['options'] = json.loads(opt)
              dev['configfile'] = os.path.join(g['git_dir'], Template(g['filename']).safe_substitute({'group':_g, 'name':e[0], 'address':e[1]}))              

            except Exception as e: sys.stderr.write("ERROR: error parsing line: %s  (%s)\n" % (line,e)); continue
    
            #print dev['host'].get_account()
            #print "Account"
            if not dev['host'].get_account():     #Account not spesifies on device, get best match from loginrc
              dev['host'].set_account(
                Account(
                  loginrc.get('username',dev['host'].get_address()), 
                  loginrc.get('password',dev['host'].get_address()) 
                  )
                )

            if not "authuser" in dev['options'].keys():
              dev['options']['authuser'] = loginrc.get('authuser', dev['host'].get_address())
            if not "authpass" in dev['options'].keys():
              dev['options']['authpass'] = loginrc.get('authpass', dev['host'].get_address())
            
            dev['options']['auth_account'] = Account(
              dev['options']['authuser'],
              dev['options']['authpass']
            )


            devices[e[0]] = dev              
      config_groups[_g]['devices'] = devices
  #Creating a Exscript queue and redirects all errors to systems devnull, errors are shown in log instead
  threads = config.get('system','max_threads')
  if opts.threads:
    threads = opts.threads
  try:
    threads = int(threads)
  except Exception as e:
    sys.stderr.write("ERROR: maximum threads, value(%s) is not a number: %s\n" % (threads,e))
    threads = 1
  queue = Queue(verbose=1 if opts.verbose > 1 else 0, 
                max_threads = threads,
                stderr = sys.stderr
#                stderr = open(os.devnull,'w') if opts.quiet else sys.stderr
  )
  		
  filelog = log_to_file("../log")		
  #running workflow on all devices in all groups
  jobid = 0
  for _g in config_groups:
    for _d in config_groups[_g]['devices']:
      jobid += 1
      d = config_groups[_g]['devices'][_d]

      d['job_id'] = jobid
      host =     d['host']
      workflow = d['workflow_name']
      #Activate logging and save log to memory, log will be connected to device in config_groups
      log = Logger()
      logdecorator = log_to(log)
      if opts.verbose > 1: print "RUN: queueing %s:%-20s (jobid: %s)" % (_g,_d,jobid )  
      d['log'] = log
      sleep(0.2) # fixup!  Some devices failes when threads are started to fast, sleeps 200ms between each thread-start
      d['task'] = queue.run(
                            host, 
                            logdecorator(
                                         bind(
                                              pycid.workflow.driver_map[workflow]._command_runner,     #Command to execute
                                              (_g,_d,jobid,d['options']),                              #jobinfo
                                              excallback                                               #Callback function
                                              )
                                         )
                           )

# Waiting for all queues to finish

  if opts.verbose > 1: print "Waiting for all threads to finish!"
  queue.join()

#  Print logs and save configfiles 

  for _g in config_groups:
    for _d in config_groups[_g]['devices']:
      d = config_groups[_g]['devices'][_d]
      file = d['configfile']
      status = d['log'].get_succeeded_actions() 
      #print "%s %s" % (d['log'].get_succeeded_actions(), d['log'].get_aborted_actions())
      if d['log'].get_succeeded_actions() > 0:
        try:
          with open(file, 'w') as out:
            out.write(d['result'])
        except Exception as e:
            sys.stderr.write("ERROR: Unable to save configuration for node %s on group %s to file %s (%s)\n" % (_d, _g, file, e))
        else: 
          if opts.verbose > 0: print "Save %s:%s to %s" % (_g, _d, file)
      elif d['log'].get_aborted_actions() > 0:
        sys.stderr.write("ERROR: No collected data from %s:%s (%s)\n" % (_g,_d,d['log'].get_aborted_logs()[0].exc_info[1]))
      else:
        sys.stderr.write("ERROR: Device not processed %s:%s\n" % (_g,_d))
  if opts.ipyshell: IPython.embed()



  #Destroys work queue and cleans up variables
  queue.destroy()

  
  if opts.verbose > 2: pprint(config_groups)


if __name__ == "__main__":
  main()

