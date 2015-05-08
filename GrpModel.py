from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr
import datetime
import utils
import pyca
from copy import deepcopy

class GrpModel(QtGui.QStandardItemModel):
    cname   = ["Status", "Group Name"]
    ctips   = ["?", "?"]
    colcnt  = len(cname)
    coff    = len(cname)
    statcol = 0
    namecol = 1
    mutable = 2 # The first non-frozen column
    roles   = [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ForegroundRole,
               QtCore.Qt.BackgroundRole, QtCore.Qt.ToolTipRole, QtCore.Qt.FontRole]

    def __init__(self):
        QtGui.QStandardItemModel.__init__(self)
        self.rowmap  = []
        self.nextid  = -1
        self.newids  = []
        self.newgrps = {}
        self.length  = {}
        self.edits   = {}
        self.status  = {}
        self.deletes = []
        self.grpchange()

    def getGroupId(self, index):
        return self.rowmap[index.row() / 2]
    
    def getGroup(self, index, withEdits=True):
        id = self.getGroupId(index)
        if id < 0:
            g = self.newgrps[id]             # No edits -> no need to copy!
            g['global']['len'] = self.length[id]
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
                    g['global']['len'] = self.length[id]
                except:
                    pass
        try:
            g['global']['status'] = self.status[id]
        except:
            pass
        return g

    def index2isf(self, index):
        r = index.row()
        c = index.column()
        id = self.rowmap[r/2]
        if r % 2 == 0:                 # Name and configurations
            if c == self.statcol:
                seq = 'global'
                f = 'status'
            elif c == self.namecol:
                seq = 'global'
                f = 'name'
            else:
                seq = c - self.coff
                f = 'config'
        else:                          # Ports.
            seq = c - self.coff
            f = 'port'
        return (id, seq, f)

    def setLength(self, id, v):
        self.length[id] = v
        if id < 0:
            self.newgrps[id]['global']['len'] = v
            
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
            try:
                ov = e[seq][f]
            except:
                ov = v2
            if v2 == v or (v2 == None and v == 0): # Rewrite of the original value!
                try:
                    del e[seq][f]
                    if e[seq] == {}:
                        del e[seq]
                except:
                    pass
            else:                                  # A real change!
                try:
                    e[seq][f] = v
                except:
                    e[seq] = {f: v}
            if f == 'config':
                if v == 0 and ov != 0:
                    # We're deleting an item!  Delete the port as well!
                    self.setData(self.index(index.row()+1, index.column()),
                                 QtCore.QVariant("DEFAULT"))
                    if seq + 1 == self.length[id]:
                        # We're deleting the last column of this group!
                        self.setLength(id, seq)
                        nm = max(self.length.values())
                        if nm + 2 != self.columnCount():
                            self.setColumnCount(nm + self.coff)
                            self.dataChanged.emit(self.index(0, nm + self.coff - 1),
                                                  self.index(self.rowCount() - 1, nm + self.coff - 1))
                elif v != 0 and (ov == 0 or ov == None):
                    # We're adding an item!
                    if seq == self.length[id]:
                        # We're adding a new item to the end!
                        self.setLength(id, seq + 1)
                        nm = max(self.length.values())
                        if nm + 2 != self.columnCount():
                            self.setColumnCount(nm + self.coff + 1)
                            self.addColumnHeader(nm + self.coff)
                            self.dataChanged.emit(self.index(0, nm + self.coff),
                                                  self.index(self.rowCount()-1, nm + self.coff))
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
        if r % 2 == 0:          # Name, Status, and Configurations.
            if c == self.namecol:
                flags = flags | QtCore.Qt.ItemIsEditable
            # Selecting a configuration requires calling up a dialog!
        else:                   # Ports.
            try:
                if self.getGroup(index)[c - self.coff]['config'] != 0:
                    flags = flags | QtCore.Qt.ItemIsEditable
            except:
                pass
        return flags

    def addColumnHeader(self, c):
        if c < self.coff:
            item = QtGui.QStandardItem(self.cname[c])
            item.setToolTip(self.ctips[c])
        else:
            item = QtGui.QStandardItem(str(c - self.coff + 1))
            # item.setToolTip("?")
        self.setHorizontalHeaderItem(c, item)

    def grpchange(self):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.rowmap = param.params.db.groupids[:]   # Copy!
        self.rowmap.extend(self.newids)
        self.length = {}
        for id in self.rowmap:
            if id < 0:
                self.length[id] = self.newgrps[id]['global']['len']
            else:
                self.length[id] = param.params.db.groups[id]['global']['len']
        self.setRowCount(len(self.rowmap) * 2)
        self.setColumnCount(self.coff + max(self.length.values()));
        for c in range(self.columnCount()):         # Make sure we have a header!
            self.addColumnHeader(c)
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def cfgchange(self):
        pass

    def createGrp(self, table, index):
        id = self.nextid
        self.nextid -= 1
        name = "New-Group%d" % id
        g = {"global": {"len": 0, "name": name}}
        self.newgrps[id] = g
        self.setLength(id, 0)
        self.status[id] = "N"
        r = 2 * len(self.rowmap)
        self.rowmap.append(id)
        self.setRowCount(r + 2)
        self.dataChanged.emit(self.index(r, 0), self.index(r + 1, self.coff + max(self.length.values())))

    def deleteGrp(self, table, index):
        r = index.row();
        if r % 2 == 1:
            r -= 1
        id = self.getGroupId(index)
        if id < 0:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            del self.newgrps[id]
            del self.status[id]
            del self.length[id]
            self.rowmap.remove(id)
            self.setRowCount(2 * len(self.rowmap))
            self.emit(QtCore.SIGNAL("layoutChanged()"))
        else:
            self.status[id] = 'D'
            self.dataChanged.emit(self.index(r, self.statcol), self.index(r, self.statcol))

    def undeleteGrp(self, table, index):
        id = self.getGroupId(index)
        del self.status[id]
        
    def deleteCfg(self, table, index):
        self.setData(index, QtCore.QVariant(0))

    def selectCfgOK(self, table, index):
        r = index.row()
        if r % 2 != 0:
            return False
        c = index.column()
        if c < self.coff:
            return False
        if c >= self.length[self.getGroupId(index)] + self.coff:
            return False
        return True

    def addCfgOK(self, table, index):
        r = index.row()
        if r % 2 != 0:
            return False
        return index.column() == self.length[self.getGroupId(index)] + self.coff           

    def deleteCfgOK(self, table, index):
        id = self.getGroupId(index)
        try:
            if self.status[id] == "D":
                return False
        except:
            pass
        return True

    def undeleteCfgOK(self, table, index):
        id = self.getGroupId(index)
        try:
            if self.status[id] == "D":
                return True
        except:
            pass
        return False
        
    def selectCfg(self, table, index):
        title = ("Select configuration #%d for group %s" %
                 (index.column() - self.coff + 1, self.getGroup(index)['global']['name']))
        if (param.params.cfgdialog.exec_(title) == QtGui.QDialog.Accepted):
            self.setData(index, QtCore.QVariant(param.params.cfgdialog.result))
    
    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new group", self.createGrp)
        menu.addAction("Delete this group", self.deleteGrp, self.deleteCfgOK)
        menu.addAction("Undelete this group", self.undeleteGrp, self.undeleteCfgOK)
        menu.addAction("Delete this configuration", self.deleteCfg, self.selectCfgOK)
        menu.addAction("Select new configuration", self.selectCfg, self.selectCfgOK)
        menu.addAction("Add new configuration", self.selectCfg, self.addCfgOK)
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

    def doDebug(self):
        print self.edits
        print
        print self.getGroup(self.index(0, 3))
        print
    
