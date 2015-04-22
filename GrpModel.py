from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr
import datetime
import utils
import pyca

class GrpModel(QtGui.QStandardItemModel):
    cname   = ["Group Name"]
    ctips   = ["ADD TOOLTIP!"]
    colcnt  = len(cname)
    coff    = len(cname)
    namecol = 0
    mutable = 1 # The first non-frozen column

    def __init__(self):
        QtGui.QStandardItemModel.__init__(self)
        for c in range(self.colcnt):
            i = QtGui.QStandardItem(self.cname[c])
            i.setToolTip(self.ctips[c])
            self.setHorizontalHeaderItem(c, i)
        self.grpchange()

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if (role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole and
            role != QtCore.Qt.ForegroundRole and role != QtCore.Qt.BackgroundRole and
            role != QtCore.Qt.ToolTipRole):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return QtCore.QVariant()
        r = index.row()
        c = index.column()
        if role == QtCore.Qt.ToolTipRole:
            return QtCore.QVariant()
        if role == QtCore.Qt.ForegroundRole:
            return QtCore.QVariant(param.params.black)
        if r % 2 == 0:        # The name and configurations.
            if role == QtCore.Qt.BackgroundRole:
                return QtCore.QVariant(param.params.almond)
            if c == 0:
                return QtCore.QVariant(param.params.db.groupnames[r / 2])
            else:
                g = param.params.db.groups[r / 2]
                if c <= len(g):
                    id = g[c - 1][0]
                    return QtCore.QVariant(param.params.db.getCfgName(id))
                else:
                    return QtCore.QVariant()
        else:                 # The ports.
            if role == QtCore.Qt.BackgroundRole:
                return QtCore.QVariant(param.params.white)
            if c == 0:
                return QtCore.QVariant()
            else:
                g = param.params.db.groups[(r - 1) / 2]
                if c <= len(g):
                    id = g[c - 1][1]
                    return QtCore.QVariant(param.params.objmodel.getObjName(id))
                else:
                    return QtCore.QVariant()

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
        r = index.row()
        c = index.column()
        print "Set (%d, %d) to %s" % (r, c, str(v))
        if r % 2 == 0:                 # Name and configurations
            if c == 0:
                print "New name!"
            else:
                print "New config id %d" % v
        else:                          # Ports.
            v = param.params.objmodel.getObjId(v)
            print "New port id %d" % v
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
            g = param.params.db.groups[(r - 1) / 2]
            if c >= 1 and c <= len(g):
                flags = flags | QtCore.Qt.ItemIsEditable
        return flags

    def grpchange(self):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.setRowCount(len(param.params.db.groups) * 2)
        self.setColumnCount(2 + max([len(l) for l in param.params.db.groups]))
        for c in range(1, self.columnCount()):
            item = QtGui.QStandardItem("")
            # item.setToolTip("?")
            self.setHorizontalHeaderItem(c, item)
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
        if c > len(param.params.db.groups[r/2]):
            return False
        return True

    def AddCfgOK(self, table, index):
        r = index.row()
        if r % 2 != 0:
            return False
        return index.column() == len(param.params.db.groups[r/2]) + 1           
    
    def selectCfg(self, table, index):
        title = ("Select configuration #%d for group %s" %
                 (index.column(), param.params.db.groupnames[index.row()/2]))
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
            return param.params.objmodel.getObjList(['Manual'])
