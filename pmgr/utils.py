from PyQt5 import QtCore, QtGui, QtWidgets
import threading

import kerberos
from psp.Pv import Pv
import pyca

from . import param

######################################################################
       
#
# Class to support for context menus in DropTableView.  The API is:
#     isActive(table, index)
#         - Return True is this menu should be displayed at this index
#           in the table.
#     doMenu(table, pos, index)
#         - Show/execute the menu at location pos/index in the table.
#     addAction(name, action)
#         - Create a menu item named "name" that, when selected, calls
#           action(table, index) to perform the action.
#
class MyContextMenu(QtWidgets.QMenu):
    """
    Create a conditional context menu for a TableView or HeaderView

    Constructor Parameters
    ----------------------
    isAct(table, index) : boolean
        Determine if this menu should be active at the current location.

        Parameters
        ----------
        table : TableView / HeaderView
            The current view being pointed at.

        index : QModelIndex / int
            The current location in the view.

        Returns
        -------
        active : boolean
            Return True if the menu should be displayed.
    """
    def __init__(self, isAct=None):
        QtWidgets.QMenu.__init__(self)
        self.isAct = isAct
        self.actions = []
        self.havecond = False

    def addAction(self, name, action, cond=None):
        """
        Add a menu action to the menu.

        Parameters
        ----------
        name : str
            The name of the action to be added to the menu.

        action : function
            The function to be called when the menu item is selected.

            Parameters
            ----------
            table : TableView / HeaderView
                The view being pointed at.

            index : QModelIndex / int
                The location in the view being pointed at.

            Returns
            -------
            Nothing.

        cond : function 
            A function that makes this menu item conditional.

            Parameters
            ----------
            table : TableView / HeaderView
                The view being pointed at.

            index : QModelIndex / int
                The location in the view being pointed at.

            Returns
            -------
            active : boolean
                True if this menu item should be active.
        """
        if cond != None:
            self.havecond = True
        self.actions.append((name, action, cond))
        QtWidgets.QMenu.addAction(self, name)

    def isActive(self, table, index):
        """
        Determine if this menu should be active, and if so, rebuild it
        if necessary.

        Parameters
        ----------
        table : TableView / HeaderView
            The current view being pointed at.

        index : QModelIndex / int
            The current location in the view.

        Returns
        -------
        active : boolean
            Return True if this menu should be displayed, rebuilding it
            if necessary.
        """
        if self.isAct == None or self.isAct(table, index):
            if self.havecond:
                self.clear()
                for name, action, cond in self.actions:
                    if cond == None or cond(table, index):
                        QtWidgets.QMenu.addAction(self, name)
            return True
        else:
            return False

    def doMenu(self, table, pos, index):
        """
        Display the menu at the specified position.  If an action is 
        selected, execute it.

        table : TableView / HeaderView
            The current view being pointed at.

        pos : QPoint
            The position where a context menu was requested.

        index : QModelIndex / int
            The current location in the view.

        Returns
        -------
        Nothing
        """
        if type(index) == int:
            gpos = table.horizontalHeader().viewport().mapToGlobal(pos)
        else:
            gpos = table.viewport().mapToGlobal(pos)
        selectedItem = self.exec_(gpos)
        if selectedItem != None:
            txt = selectedItem.text()
            for name, action, cond in self.actions:
                if txt == name:
                    action(table, index)
                    return

######################################################################

#
# Utility functions to deal with PVs.
#

def caput(pvname,value,timeout=1.0,**kw):
    try:
        pv = Pv(pvname)
        pv.connect(timeout)
        pv.get(ctrl=False, timeout=timeout)
        try:
            if kw['enum']:
                pv.set_string_enum(True)
        except:
            pass
        pv.put(value, timeout=timeout)
        pv.disconnect()
    except pyca.pyexc as e:
        print('pyca exception: %s' %(e))
    except pyca.caexc as e:
        print('channel access exception: %s' %(e))

def caget(pvname,timeout=1.0,**kw):
    try:
        pv = Pv(pvname)
        pv.connect(timeout)
        try:
            if kw['enum']:
                pv.set_string_enum(True)
        except:
            pass
        pv.get(ctrl=False, timeout=timeout)
        v = pv.value
        pv.disconnect()
        return v
    except pyca.pyexc as e:
        print('pyca exception: %s' %(e))
        return None
    except pyca.caexc as e:
        print('channel access exception: %s' %(e))
        return None

def __get_callback(pv, e):
    if e is None:
        pv.get_done.set()
        pv.disconnect()
        pyca.flush_io()

#
# Do an asynchronous caget, but notify a threading.Event after it
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
    except pyca.pyexc as e:
        print('pyca exception: %s' %(e))
        return None
    except pyca.caexc as e:
        print('channel access exception: %s' %(e))
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
            pv.get(ctrl=False, timeout=timeout)
        return pv
    except:
      return None

def __connect_callback(pv, isconn):
    if (isconn):
        pv.connect_cb = pv.save_connect_cb
        if pv.connect_cb:
            pv.connect_cb(isconn)
        pv.get(ctrl=False, timeout=-1.0)

def __getevt_callback(pv, e=None):
    if pv.handler:
        pv.handler(pv, e)
    if e is None:
        pv._Pv__getevt_handler(e)
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

#
# Go through a list of dictionaries and create a 'cfgname' name for the
# specified 'config' idx.
#
def fixName(l, idx, name):
    for d in l:
        try:
            if d['config'] == idx:
                d['cfgname'] = name
        except:
            pass

#
# Determine if the current user has the authority to modify a record.
#
def permission():
    return param.params.user in param.params.auth_users

#
# Check if the user/password pair is valid.  This is actually not terribly secure (the KDC can
# be spoofed), but it's really close enough for our purposes.
#
def authenticate_user(user, password):
    try:
        if kerberos.checkPassword(user, password, "krbtgt/SLAC.STANFORD.EDU", "SLAC.STANFORD.EDU"):
            return True
    except:
        pass
    return False
