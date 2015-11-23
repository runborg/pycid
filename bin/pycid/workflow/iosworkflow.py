import IPython
import re
from pycid.workflow.workflow import Workflow
from Exscript.util.match import first_match
class iosWorkflow(Workflow):
  _config = {
    "filter_pw":1,
  }
  def __init__(self):
    Workflow.__init__(self, 'ios')

  def command_runner(self):
    """
    Commands to be executed
    """
    self.local.conn.set_driver('ios')   #This is the IOS driver
#    print self.local.opts
    self.local.conn.login(app_account=self.local.opts['auth_account'])
    self.local.conn.execute("term len 0")
    self.local.result += "!DEVICE: %s\n" % self.local.device
    self.local.result += "!GROUP:  %s\n" % self.local.group
    self.local.result += self.cmd("show version", self.version)
    self.local.result += self.cmd("show running-config", self.config)


    
  def version(self, resp):
    ret = ""
    # Get system image name
    if not isinstance(resp, str): 
      print "No version found"
      return ""
    for line in resp.splitlines():
      #print "!%s" % line
      a = first_match(line, r'System image file is "([^\"]*)"', re.I)
      if a: ret +=  "!IMAGE: %s\n" % a; continue

      a = first_match(line, r'^(Cisco )?IOS .* Software,? \(([A-Za-z0-9_-]*)\), .*Version\s+(.*)$', re.I)
      if a[1]: ret += "!IMAGE: Software %s, %s\n" % (a[1], a[2]); continue

      a = first_match(line, r'^ROM:.*', re.I)
      if a: ret += "!ROM: %s\n" % a; continue

      a = first_match(line, r'BOOTLDR:.*', re.I)
      if a: ret += "!BOOTLDR: %s\n" % a; continue
      
      a = first_match(line, r'(\S+(?:\sseries)?)\s+(?:\((\S+)\)\s+processor|\(revision[^)]+\)).*\s+with (\S+k) bytes', re.I)
      if a[0]: ret += "!TYPE: %s (%s)\n!MEMORY: %s\n" % (a[0], a[1], a[2]) ; continue

      a = first_match(line, r'^Configuration register is (.*)$')
      if a: ret += "!CONFREG: %s\n" % a; continue
    
    return ret


  def config(self,resp):
    ret = ""
    if not isinstance(resp, str): 
      print "No Config found"
      return ""
    remove = [
      "^\!",				#Remove comments
      "^Time: ",			#Remove timestamp from nxos
      "^show running-config",
      "^Building configuration",
      "Current configuration \: \d+ bytes",
    ]
    
    #Find hostname and put it on top.
    
    
    
    for line in resp.splitlines():
      #Remove lines matcing "remove" variable
      r = False
      for _remove in remove:
        if re.search(_remove,line): r = True
      if r: continue
      
      #Remove Timestamp from NX-OS
#      if re.search("^Time: ",line): continue


      #Removing passwords from configuration
      a = first_match(line, "^((enable )?(password|passwd)( level \d+)?)", re.I)
      if a[0] and self._config["filter_pw"] >= 1:
        ret += "!%s <removed>\n" % a[0]
        continue  
      a = first_match(line, "^(username (\S+)(\s.*)? secret)", re.I)
      if a[0] and self._config["filter_pw"] >= 1:
        ret += "!%s <removed>\n" % a[0]
        continue
      a = first_match(line, "^(enable secret) ", re.I)
      if a and self._config["filter_pw"] >= 1:
        ret += "!%s <removed>\n" % a
        continue
      a = first_match(line, "^(username (\S+)(\s.*)? (privilege \d+ )?(password|secret) )((\d) \S+|\S+)", re.I)
      if a[0] and self._config["filter_pw"] >= 1:
        ret += "!%s <removed>\n" % a[0]
        continue
      
      a = first_match(line, "^hostname", re.I)
      if a:
        ret += "%s\n" % a
        continue

      
        
      ret += "%s\n" % line
    return ret
