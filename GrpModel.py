from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr
import datetime
import utils
import pyca
from copy import deepcopy

class GrpModel(QtGui.QStandardItemModel):
    cname   = ["Group Name"]
    ctips   = ["ADD TOOLTIP!"]
    colcnt  = len(cname)
    coff    = len(cname)
    namecol = 0
    mutable = 1 # The first non-frozen column
    roles   = [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ForegroundRole,
               QtCore.Qt.BackgroundRole, QtCore.Qt.ToolTipRole, QtCore.Qt.FontRole]

    def __init__(self):
        QtGui.QStandardItemModel.__init__(self)
        for c in range(self.colcnt):
            i = QtGui.QStandardItem(self.cname[c])
            i.setToolTip(self.ctips[c])
            self.setHorizontalHeaderItem(c, i)
        self.newids  = []
        self.newgrps = {}
        self.maxnew  = 0
        self.edits   = {}
        self.grpchange()

    def getGroup(self, index, withEdits=True):
        id = self.rowmap[index.row() / 2]
        if id < 0:
            g = self.newgrps[id]             # No edits -> no need to copy!
        else:
            g = deepcopy(param.params.db.groups[id])
            if withEdits:
                try:
                    e = self.edits[id]
                    for (k, v) in e.items():
                        try:
                            g[k].update(v)
                        except:
                            g[k] = v
                except:
                    pass
        return g

    def index2isf(self, index):
        r = index.row()
        c = index.column()
        id = self.rowmap[r/2]
        if r % 2 == 0:                 # Name and configurations
            if c == 0:
                seq = 'global'
                f = 'name'
            else:
                seq = c - 1
                f = 'config'
        else:                          # Ports.
            seq = c - 1
            f = 'port'
        return (id, seq, f)
        
    def data(self, index, role = QtCore.Qt.DisplayRole):
        if (not role in self.roles):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return QtCore.QVariant()
        (id, seq, f) = self.index2isf(index)
        if role == QtCore.Qt.ForegroundRole:
            if id < 0:
                return QtCore.QVariant(param.params.blue)
            try:
                v = self.edits[id][seq][f]
                return QtCore.QVariant(param.params.red)
            except:
                return QtCore.QVariant(param.params.black)
        if role == QtCore.Qt.BackgroundRole:
            if f == 'port':
                return QtCore.QVariant(param.params.white)
            else:
                return QtCore.QVariant(param.params.almond)
        if role == QtCore.Qt.ToolTipRole:
            return QtCore.QVariant()
        if role == QtCore.Qt.FontRole:
            if f == 'name':
                f = QtGui.QFont()
                f.setBold(True)
                return QtCore.QVariant(f)
            else:
                return QtCore.QVariant()
        try:
            v = self.getGroup(index)[seq][f]
        except:
            return QtCore.QVariant()
        if f == 'config':
            v = param.params.db.getCfgName(v)
            if v == "DEFAULT":
                v = ""
        if f == 'port':
            v = param.params.objmodel.getObjName(v)
            if v == "DEFAULT":
                v = ""
        return QtCore.QVariant(v)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole:
            return QtGui.QStandardItemModel.setData(self, index, value, role)
        t = value.type()
        if t == QtCore.QMetaType.QString:
            v = str(value.toString())
        elif t == QtCore.QMetaType.Int:
            (v, ok) = value.toInt()
        elif t == QtCore.QMetaType.Double:
            (v, ok) = value.toDouble()
        elif t == QtCore.QMetaType.Void:
            v = None
        else:
            print "Unexpected QVariant type %d" % value.type()
            return False
        (id, seq, f) = self.index2isf(index)
        if f == 'port':
            v = param.params.objmodel.getObjId(v)
        if v == "DEFAULT":
            v = ""
        if id < 0:                   # A new, unsaved group can be freely edited.
            try:
                self.newgrps[id][seq][f] = v
            except:
                self.newgrps[id][seq] = {f: v}
        else:                        # An existing group.
            try:
                e = self.edits[id]
            except:
                e = {}
            g = param.params.db.groups[id]
            try:
                v2 = g[seq][f]
            except:
                v2 = None
            print v, v2
            if v2 == v or (v2 == None and v == 0): # Rewrite of the original value!
                try:
                    del e[seq][f]    # Delete any edit.
                    if e[seq] == {}:
                        del e[seq]
                except:
                    pass
                print "D ", seq, self.getGroup(index)['global']['len'], self.maxnew, param.params.db.maxgrp
                if seq + 1 == self.getGroup(index)['global']['len'] and f == 'config':
                    print "Delete last?"
                    print self.edits
            else:                    # A real change!
                try:
                    e[seq][f] = v
                except:
                    e[seq] = {f: v}
                print "A ", seq, self.getGroup(index)['global']['len'], self.maxnew, param.params.db.maxgrp
                if seq == self.getGroup(index)['global']['len']:
                    try:
                        e['global']['len'] = seq + 1
                    except:
                        e['global'] = {'len': seq + 1}
                    if seq == max(self.maxnew, param.params.db.maxgrp):
                        print "Add column!"
                        self.maxnew = seq + 1
                        self.setColumnCount(self.maxnew + 2)
                        self.addColumnHeader(self.maxnew + 1)
                        self.dataChanged.emit(self.index(0, self.maxnew + 1),
                                              self.index(self.rowCount()-1, self.maxnew + 1))
            if e == {}:
                try:
                    del self.edits[id]
                except:
                    pass
            else:
                self.edits[id] = e
        self.dataChanged.emit(index, index)
        return True

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if not index.isValid():
            return flags
        r = index.row()
        c = index.column()
        if r % 2 == 0:          # Name and Configurations.
            if c == 0:
                flags = flags | QtCore.Qt.ItemIsEditable
            # Selecting a configuration requires calling up a dialog!
        else:                   # Ports.
            g = self.getGroup(index)
            if c >= 1 and c <= g['global']['len']:
                flags = flags | QtCore.Qt.ItemIsEditable
        return flags

    def addColumnHeader(self, c):
        item = QtGui.QStandardItem("")
        # item.setToolTip("?")
        self.setHorizontalHeaderItem(c, item)

    def grpchange(self):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.rowmap = param.params.db.groupids[:]   # Copy!
        self.rowmap.extend(self.newids)
        self.setRowCount(len(self.rowmap) * 2)
        self.setColumnCount(2 + max(self.maxnew, param.params.db.maxgrp))
        for c in range(1, self.columnCount()):         # Make sure we have a header!
            self.addColumnHeader(c)
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def cfgchange(self):
        pass

    def create(self, table, index):
        pass

    def delete(self, table, index):
        pass

    def selectCfgOK(self, table, index):
        r = index.row()
        if r % 2 != 0:
            return False
        c = index.column()
        if c == 0:
            return False
        if c > self.getGroup(index)['global']['len']:
            return False
        return True

    def AddCfgOK(self, table, index):
        r = index.row()
        if r % 2 != 0:
            return False
        return index.column() == self.getGroup(index)['global']['len'] + 1           
    
    def selectCfg(self, table, index):
        title = ("Select configuration #%d for group %s" %
                 (index.column(), self.getGroup(index)['global']['name']))
        if (param.params.cfgdialog.exec_(title) == QtGui.QDialog.Accepted):
            self.setData(index, QtCore.QVariant(param.params.cfgdialog.result))
    
    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new group", self.create)
        menu.addAction("Delete this group", self.delete)
        menu.addAction("Select new configuration", self.selectCfg, self.selectCfgOK)
        menu.addAction("Add new configuration", self.selectCfg, self.AddCfgOK)
        table.addContextMenu(menu)
        colmgr.addColumnManagerMenu(table, [], False)

    def editorInfo(self, index):
        r = index.row()
        c = index.column()
        if r % 2 == 0:          # Name and Configurations.
            return str          # The name is a string, the rest aren't editable!
        else:                   # Ports.
            l = param.params.objmodel.getObjList(['Manual'])
            if l[0] == "DEFAULT":
                l[0] = ""
            return l
