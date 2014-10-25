#!/usr/bin/env python
import utils

try:
    utils.init()

    print utils.getTables()
    
    (d, m) = utils.getConfiguration("test2", "ims_motor_tpl")
    for k in d.keys():
        print "%s = %s --> %s" % (k, str(d[k]), m[k])
        
except:
    pass
finally:
    utils.finish()

