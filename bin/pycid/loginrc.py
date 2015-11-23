import re as _re
from pprint import pprint as _pprint
import mfnmatch as _mfnmatch

class propertyNotFound:
  pass


class loginrc(object):
  _opts = dict()
  def __init__(self,config_file):
    self.open(config_file)

  def open(self,config_file):
    with open(config_file, "r") as f:
      for l in f:
        if l.startswith("add"):
          line = l.strip().split(None, 3)
          if line[1] in self._opts.keys():
            self._opts[line[1]][line[2]] = line[3:]
          else:
            self._opts[line[1]] = {line[2]: line[3:]}
          
          
          
          
  
  def get(self,property, hostname):
    if not property in self._opts.keys():
      raise propertyNotFound
    #print hostname
    #print self._opts[property].keys()
    match = _mfnmatch.longest(hostname, self._opts[property].keys())
    #print type(match)
    if not isinstance(match, str): raise Exception
    
    return self._opts[property][match][0]
  
  def get_all(self):
    return self._opts
