from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr
import datetime
import utils
import pyca
from copy import deepcopy

class GrpModel(QtGui.QStandardItemModel):
    cname   = ["Status", "Active", "Group Name"]
    cfld    = ["status", "active", "name"]
    ctips   = ["D = Deleted\nM = Modified\nN = New", "Group is in use?", "Group name"]
    colcnt  = len(cname)
    coff    = len(cname)
    statcol = 0
    actvcol = 1
    namecol = 2
    mutable = 3 # The first non-frozen column
    roles   = [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ForegroundRole,
               QtCore.Qt.BackgroundRole, QtCore.Qt.ToolTipRole, QtCore.Qt.FontRole,
               QtCore.Qt.CheckStateRole]

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
        if isinstance(index, QtCore.QModelIndex):
            id = self.getGroupId(index)
        else:
            id = index
        if id < 0:
            g = self.newgrps[id]             # No edits -> no need to copy!
            g['global']['len'] = self.length[id]
        else:
            g = deepcopy(param.params.pobj.groups[id])
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
        g['global']['status'] = self.status[id]
        return g

    def index2isf(self, index):
        r = index.row()
        c = index.column()
        id = self.rowmap[r/2]
        if r % 2 == 0:                 # Name and configurations
            if c < self.coff:
                seq = 'global'
                f = self.cfld[c]
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
            # We'll make this smarter later!
            return QtGui.QStandardItemModel.data(self, index, role)
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
        if role == QtCore.Qt.CheckStateRole:
            if f == 'active':
                if v == 0:
                    return QtCore.Qt.Unchecked
                else:
                    return QtCore.Qt.Checked
            else:
                return QtCore.QVariant()
        if f == 'active':
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
        if role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole and role != QtCore.Qt.CheckStateRole:
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
        if f == 'active':
            if v == QtCore.Qt.Checked:
                v = 1
            else:
                v = 0
        if id < 0:                   # A new, unsaved group can be freely edited.
            try:
                ov = self.newgrps[id][seq][f]
            except:
                ov = None
            try:
                self.newgrps[id][seq][f] = v
            except:
                self.newgrps[id][seq] = {f: v}
        else:                        # An existing group.
            try:
                e = self.edits[id]
            except:
                e = {}
            hadedit = (e != {})
            g = param.params.pobj.groups[id]
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
            if e == {}:
                if hadedit:
                    self.status[id] = self.status[id].replace("M", "")
                try:
                    del self.edits[id]
                except:
                    pass
            else:
                if not hadedit:
                    self.status[id] = "".join(sorted("M" + self.status[id]))
                self.edits[id] = e
        if f == 'config':
            if v == 0 and ov != 0:
                # We're deleting an item!  Delete the port as well!
                self.setData(self.index(index.row()+1, index.column()),
                             QtCore.QVariant("DEFAULT"))
                if seq + 1 == self.length[id]:
                    # We're deleting the last column of this group!
                    self.setLength(id, seq)
                    nm = max(self.length.values())
                    if self.coff + nm + 1 != self.columnCount():
                        self.setColumnCount(nm + self.coff + 1)
                        self.dataChanged.emit(self.index(0, nm + self.coff - 1),
                                              self.index(self.rowCount() - 1, nm + self.coff - 1))
            elif v != 0 and (ov == 0 or ov == None):
                # We're adding an item!
                if seq == self.length[id]:
                    # We're adding a new item to the end!
                    self.setLength(id, seq + 1)
                    nm = max(self.length.values())
                    if self.coff + nm + 1 != self.columnCount():
                        self.setColumnCount(nm + self.coff + 1)
                        self.addColumnHeader(nm + self.coff)
                        self.dataChanged.emit(self.index(0, nm + self.coff),
                                              self.index(self.rowCount()-1, nm + self.coff))
        self.dataChanged.emit(index, index)
        idx = self.index(index.row() & ~1, self.statcol)
        self.dataChanged.emit(idx, idx)
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
            elif c == self.actvcol:
                flags = flags | QtCore.Qt.ItemIsUserCheckable
        else:                   # Ports.
            try:
                # Selecting a configuration requires calling up a dialog!
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
        self.rowmap = param.params.pobj.groupids[:]   # Copy!
        self.rowmap.extend(self.newids[:])
        self.length = {}
        self.status = {}
        for id in self.rowmap:
            if id < 0:
                self.length[id] = self.newgrps[id]['global']['len']
                self.status[id] = "N"
            else:
                self.length[id] = param.params.pobj.groups[id]['global']['len']
                try:
                    k = self.edits[id].keys()
                    if 'global' in k:
                        k.remove('global')
                    k = max(k)
                    if k + 1 > self.length[id]:
                        self.length[id] = k + 1
                except:
                    pass
                self.status[id] = ""
                if id in self.deletes:
                    self.status[id] += "D"
                try:
                    if self.edits[id] != {}:
                        self.status[id] += "M"
                except:
                    pass
        self.setRowCount(len(self.rowmap) * 2)
        self.setColumnCount(self.coff + max(self.length.values()) + 1);
        for c in range(self.columnCount()):         # Make sure we have a header!
            self.addColumnHeader(c)
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def cfgchange(self):
        pass

#############################
#
# Context Menus
#
#############################

    def createGrp(self, table, index):
        id = self.nextid
        self.nextid -= 1
        name = "New-Group%d" % id
        g = {"global": {"len": 0, "name": name, "active": 0}}
        self.newgrps[id] = g
        self.setLength(id, 0)
        self.status[id] = "N"
        r = 2 * len(self.rowmap)
        self.newids.append(id)
        self.rowmap.append(id)
        self.setRowCount(r + 2)
        self.dataChanged.emit(self.index(r, 0), self.index(r + 1, self.coff + max(self.length.values())))

    def deleteGrpOK(self, table, index):
        id = self.getGroupId(index)
        if "D" in self.status[id]:
            return False
        else:
            return True

    def deleteGrp(self, table, index):
        r = index.row();
        if r % 2 == 1:
            r -= 1
        id = self.getGroupId(index)
        if id < 0:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.newids.remove(id)
            del self.newgrps[id]
            del self.status[id]
            del self.length[id]
            self.rowmap.remove(id)
            self.setRowCount(2 * len(self.rowmap))
            self.emit(QtCore.SIGNAL("layoutChanged()"))
        else:
            self.deletes.append(id)
            self.status[id] = "".join(sorted("D" + self.status[id]))
            self.dataChanged.emit(self.index(r, self.statcol), self.index(r, self.statcol))

    def undeleteGrpOK(self, table, index):
        id = self.getGroupId(index)
        if "D" in self.status[id]:
            return True
        else:
            return False

    def undeleteGrp(self, table, index):
        id = self.getGroupId(index)
        self.deletes.remove(id)
        self.status[id] = self.status[id].replace("D", "")

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
        
    def deleteCfg(self, table, index):
        self.setData(index, QtCore.QVariant(0))
        
    def selectCfg(self, table, index):
        title = ("Select configuration #%d for group %s" %
                 (index.column() - self.coff + 1, self.getGroup(index)['global']['name']))
        if (param.params.cfgdialog.exec_(title) == QtGui.QDialog.Accepted):
            self.setData(index, QtCore.QVariant(param.params.cfgdialog.result))

    def commitOK(self, table, index):
        id = self.getGroupId(index)
        return id < 0 or "M" in self.status[id] or "D" in self.status[id]

    #
    # Try to commit a change.  Assume we are in a transaction already.
    #
    def commit(self, id):
        g = self.getGroup(id)
        try:
            name = self.edits[id]['global']['name']
        except:
            name = g['global']['name']
        if name[0:10] == "New-Group-":
            param.params.pobj.transaction_error("Group cannot be named %s!" % name)
            return
        for d in g.values():
            try:
                if d['config'] < 0:
                    param.params.pobj.transaction_error("New configuration %s must be committed before %s!" %
                                                      (param.params.db.getCfgName(d['config']), name))
                    return
            except:
                pass
        # Check if otherwise OK!  A group should have all configurations unique.
        # They don't have to all be defined though, if we only want to save it!
        cfgs = []
        for d in g.values():
            try:
                c = d['config']
                if c != 0 and c in cfgs:
                    param.params.pobj.transaction_error("Group has multiple configurations named %s!" %
                                                      param.params.db.getCfgName(c))
                    return
                cfgs.append(c)
            except:
                pass   # Must be 'global' dictionary!
        if 'D' in self.status[id]:
            result = param.params.pobj.groupDelete(id)
        elif 'N' in self.status[id]:
            result = param.params.pobj.groupInsert(g)
        elif 'M' in self.status[id]:
            result = param.params.pobj.groupUpdate(id, g)
        if result:
            self.grpChangeDone(id)

    def commitall(self, verify=True):
        # Do we want to verify?
        for (id, s) in self.status.items():
            if 'D' in s:
                self.commit(id)
        for (id, s) in self.status.items():
            if ('N' in s or 'M' in s) and not 'D' in s:  # Paranoia.  We should never have DM or DN.
                self.commit(id)

    def commitone(self, table, index):
        param.params.db.start_transaction()
        id = self.getGroupId(index)
        self.commit(id)
        if param.params.db.end_transaction():
            return True
        else:
            return False

    def grpChangeDone(self, id):
        if id < 0:
            self.newids.remove(id)
            del self.newgrps[id]
            del self.status[id]
            del self.length[id]
            self.rowmap = param.params.pobj.groupids[:]  # This is a temporary measure until we re-read the config.
            self.rowmap.extend(self.newids[:])
            self.setRowCount(len(self.rowmap) * 2)
        else:
            try:
                del self.edits[id]
            except:
                pass
            if id in self.deletes:
                self.deletes.remove(id)
            else:
                self.status[id] = ""

    def applyOK(self, table, index):
        id = self.getGroupId(index)
        g = self.getGroup(index)
        return not "D" in self.status[id] and g['global']['active'] == 1

    def checkPorts(self, g, ports):
        for d in g.values():
            try:
                p = d['port']
                if p != 0 and p in ports:
                    param.params.pobj.transaction_error("Multiple ports named %s in use!" %
                                                        param.params.objmodel.getObjName(p))
                else:
                    ports.append(p)
            except:
                pass   # Must be 'global' dictionary!

    def apply(self, g):
        for d in g.values():
            try:
                if d['port'] != 0:
                    param.params.objmodel.setCfg(d['port'], d['config'])
            except:
                pass # Must be 'global'!

    def applyone(self, table, index):
        param.params.db.start_transaction()
        id = self.getGroupId(index)
        g = self.getGroup(index) # If we commit, the index might not be valid, so better get the values now.
        if id < 0 or "M" in self.status[id]:
            self.commit(id)
        self.checkPorts(g, [])
        if not param.params.db.end_transaction():
            return
        self.apply(g)

    def applyall(self, table, index):
        param.params.db.start_transaction()
        self.commitall()
        if not param.params.db.end_transaction():
            return
        param.params.db.start_transaction()
        ports = []
        for id in self.rowmap:
            g = self.getGroup(id)
            if g['global']['active'] == 1:
                self.checkPorts(g, ports)
        if not param.params.db.end_transaction():
            return
        for id in self.rowmap:
            g = self.getGroup(id)
            if g['global']['active'] == 1:
                self.apply(g)

    def revertOK(self, table, index):
        id = self.getGroupId(index)
        return "M" in self.status[id]

    def revertone(self, table, index):
        id = self.getGroupId(index)
        try:
            del self.edits[id]
        except:
            pass
        self.length[id] = param.params.pobj.groups[id]['global']['len']
        self.status[id] = ""
        nm = max(self.length.values())
        if self.coff + nm + 1 != self.columnCount():
            self.setColumnCount(nm + self.coff + 1)
            self.dataChanged.emit(self.index(0, nm + self.coff),
                                  self.index(self.rowCount()-1, nm + self.coff))
        else:
            r = index.row() - index.row() % 2
            self.dataChanged.emit(self.index(r, 0), self.index(r + 1, self.columnCount()))

    def revertall(self):
        self.nextid  = -1
        self.newids  = []
        self.newgrps = {}
        self.edits   = {}
        self.deletes = []
        self.grpchange()
        
    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new group", self.createGrp)
        menu.addAction("Delete this group", self.deleteGrp, self.deleteGrpOK)
        menu.addAction("Undelete this group", self.undeleteGrp, self.undeleteGrpOK)
        menu.addAction("Delete this configuration", self.deleteCfg, self.selectCfgOK)
        menu.addAction("Select new configuration", self.selectCfg, self.selectCfgOK)
        menu.addAction("Add new configuration", self.selectCfg, self.addCfgOK)
        menu.addAction("Commit this group", self.commitone, self.commitOK)
        menu.addAction("Revert this group", self.revertone, self.revertOK)
        menu.addAction("Apply this group", self.applyone, self.applyOK)
        menu.addAction("Apply all", self.applyall)
        table.addContextMenu(menu)
        colmgr.addColumnManagerMenu(table, [], False, False)

    def editorInfo(self, index):
        r = index.row()
        c = index.column()
        if r % 2 == 0:          # Name and Configurations.
            if c == self.namecol:
                return str          # The name is a string.
            if c == self.actvcol:
                return int          # This needs to become a checkbox!
        else:                   # Ports.
            l = param.params.objmodel.getObjList(['Manual'])
            if l[0] == "DEFAULT":
                l[0] = ""
            return l

    def cfgrenumber(self, old, new):
        for d in self.edits.values():
            for dd in d.values():
                try:
                    if dd['config'] == old:
                        dd['config'] = new
                except:
                    pass
        for d in self.newgrps.values():
            for dd in d.values():
                try:
                    if dd['config'] == old:
                        dd['config'] = new
                except:
                    pass

    def doDebug(self):
        print self.edits
        param.params.debug = not param.params.debug
