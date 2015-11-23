import inspect
from pycid.workflow.workflow import Workflow
from pycid.workflow.iosworkflow import iosWorkflow



driver_classes = []
drivers        = []
driver_map     = {}



def isdriver(o):
  return inspect.isclass(o) and issubclass(o, Workflow) and not o is Workflow

def add_driver(cls):
  driver = cls()
  driver_classes.append(driver)
  driver_map[driver.name] = driver


for name,obj in locals().items():
  if isdriver(obj):
    add_driver(obj)
    
#driver_map['unknown'] = driver_map['ios']
