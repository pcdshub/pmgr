from psp.Pv import Pv
import pyca
import threading

#
# Utility functions to deal with PVs.
#

def caput(pvname,value,timeout=1.0):
    try:
        pv = Pv(pvname)
        pv.connect(timeout)
        pv.get(ctrl=False, timeout=timeout)
        pv.put(value, timeout)
        pv.disconnect()
    except pyca.pyexc, e:
        print 'pyca exception: %s' %(e)
    except pyca.caexc, e:
        print 'channel access exception: %s' %(e)

def caget(pvname,timeout=1.0):
    try:
        pv = Pv(pvname)
        pv.connect(timeout)
        pv.get(ctrl=False, timeout=timeout)
        v = pv.value
        pv.disconnect()
        return v
    except pyca.pyexc, e:
        print 'pyca exception: %s' %(e)
        return None
    except pyca.caexc, e:
        print 'channel access exception: %s' %(e)
        return None

def __get_callback(pv, e):
    if e is None:
        pv.get_done.set()
        pv.disconnect()
        pyca.flush_io()

#
# Do an assynchronous caget, but notify a threading.Event after it
# completes instead of just waiting.
#
def caget_async(pvname):
    try:
        pv = Pv(pvname)
        pv.get_done = threading.Event()
        pv.connect_cb = lambda isconn: __connect_callback(pv, isconn)
        pv.getevt_cb = lambda e=None: __get_callback(pv, e)
        pv.connect(-1)
        return pv
    except pyca.pyexc, e:
        print 'pyca exception: %s' %(e)
        return None
    except pyca.caexc, e:
        print 'channel access exception: %s' %(e)
        return None

def connectPv(name, timeout=-1.0):
    try:
        pv = Pv(name)
        if timeout < 0:
            pv.save_connect_cb = pv.connect_cb
            pv.connect_cb = lambda isconn: __connect_callback(pv, isconn)
            pv.connect(timeout)
        else:
            pv.connect(timeout)
            pv.get(False, timeout)
        return pv
    except:
      return None

def __connect_callback(pv, isconn):
    if (isconn):
        pv.connect_cb = pv.save_connect_cb
        if pv.connect_cb:
            pv.connect_cb(isconn)
        pv.get(False, -1.0)

def __getevt_callback(pv, e=None):
    if pv.handler:
        pv.handler(pv, e)
    if e is None:
        pv.getevt_cb = None
        pv.monitor(pyca.DBE_VALUE)
        pyca.flush_io()

def __monitor_callback(pv, e=None):
    pv.handler(pv, e)
        
def monitorPv(name,handler):
    try:
        pv = connectPv(name)
        pv.handler = handler
        pv.getevt_cb = lambda  e=None: __getevt_callback(pv, e)
        pv.monitor_cb = lambda e=None: __monitor_callback(pv, e)
        return pv
    except:
        return None
