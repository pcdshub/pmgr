from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr

class ObjModel(QtGui.QStandardItemModel):
    cname   = ["Status", "Name", "Config", "PV Base"]
    cfld    = ["status", "name", "linkname", "rec_base"]
    coff    = len(cname)
    statcol = 0
    namecol = 1
    cfgcol  = 2
    mutable = 2
    
    def __init__(self, db, ui):
        QtGui.QStandardItemModel.__init__(self)
        self.db = db
        self.ui = ui
        self.id2idx = None
        self.edits = {}
        self.lastsort = (0, QtCore.Qt.DescendingOrder)
        db.setModel(self)
        # Setup headers
        self.setColumnCount(self.db.objfldcnt + self.coff)
        self.setRowCount(len(self.db.objs))
        font = QtGui.QFont()
        font.setBold(True)
        for c in range(self.db.objfldcnt + self.coff):
            if c < self.coff:
                self.setHorizontalHeaderItem(c, QtGui.QStandardItem(self.cname[c]))
            else:
                self.setHorizontalHeaderItem(c, QtGui.QStandardItem(self.db.objflds[c-self.coff]['alias']))
        self.setHeaderData(self.statcol, QtCore.Qt.Horizontal,
                           QtCore.QVariant("C = All PVs Connected\nM = Modified"),
                           QtCore.Qt.ToolTipRole)

    def index2db(self, index):
        c = index.column()
        if c < self.coff:
            return (self.db.objs[index.row()]['id'], self.cfld[c])
        else:
            return (self.db.objs[index.row()]['id'], self.db.objflds[c-self.coff]['fld'])
        
    def data(self, index, role = QtCore.Qt.DisplayRole):
        if (role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole and
            role != QtCore.Qt.ForegroundRole):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return QtCore.QVariant()
        try:
            d = self.db.objs[index.row()]
            (idx, f) = self.index2db(index)
            try:
                v = self.edits[idx][f]
                if role == QtCore.Qt.ForegroundRole:
                    return QtCore.QVariant(param.params.red)
                else:
                    return QtCore.QVariant(v)
            except:
                v = d[f]             # Actual value
                if role != QtCore.Qt.ForegroundRole:
                    return QtCore.QVariant(v)
                v2 = d['origcfg'][f] # Configured value
                if param.equal(v, v2):
                    return QtCore.QVariant(param.params.black)
                else:
                    return QtCore.QVariant(param.params.blue)
        except:
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
        else:
            print "Unexpected QVariant type %d" % value.type()
            return False
        (idx, f) = self.index2db(index)
        try:
            d = self.edits[idx]
        except:
            d = {}
        hadedit = (d != {})
        # OK, the config/linkname thing is slightly weird.  The field name for our index is
        # 'linkname', but we are passing an int that should go to 'link'.  So we need to
        # change *both*!
        if f == 'linkname':
            vlink = v
            v = self.db.id2name[vlink]
        try:
            del d[f]
            if f == 'linkname':
                del d['config']
        except:
            pass
        r = self.db.objs[index.row()]
        if index.column() < self.coff:
            dd = r
        else:
            dd = r['origcfg']
        if not param.equal(v, dd[f]):
            d[f] = v
            if f == 'linkname':
                d['config'] = vlink
            if not hadedit:
                r['status'] = "".join(sorted("M" + r['status']))
                statidx = self.index(index.row(), self.statcol)
                self.dataChanged.emit(index, index)
        else:
            if hadedit and d == {}:
                r['status'] = r['status'].replace("M", "")
                statidx = self.index(index.row(), self.statcol)
                self.dataChanged.emit(index, index)
        if d != {}:
            self.edits[idx] = d
        else:
            try:
                del self.edits[idx]
            except:
                pass
        self.dataChanged.emit(index, index)
        return True
        
    def value(self, entry, c, display=True):
        if c < self.coff:
            return entry[self.cfld[c]]
        else:
            return entry[self.db.objflds[c-self.coff]['fld']]

    def sort(self, Ncol, order):
        if (Ncol, order) != self.lastsort:
            self.lastsort = (Ncol, order)
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.db.objs = sorted(self.db.objs, key=lambda d: self.value(d, Ncol))
            if order == QtCore.Qt.DescendingOrder:
                self.db.objs.reverse()
            self.makeidx()
            self.emit(QtCore.SIGNAL("layoutChanged()"))

    def makeidx(self):
        d = {}
        for i in range(len(self.db.objs)):
            d[self.db.objs[i]['id']] = i
        self.id2idx = d

    def objchange(self):
        print "ObjModel has object change!"
        self.sort(self.lastsort[0], self.lastsort[1])

    def cfgchange(self):
        print "ObjModel has config change!"
        # This is really a sledgehammer.  Maybe we should check what really needs changing?
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def pvchange(self, id, fldidx):
        if self.id2idx == None:
            self.makeidx()
        idx = self.index(self.id2idx[id], fldidx + self.coff)
        self.dataChanged.emit(idx, idx)

    def statchange(self, id):
        if self.id2idx == None:
            self.makeidx()
        idx = self.index(self.id2idx[id], self.statcol)
        self.dataChanged.emit(idx, idx)

    def haveNewName(self, idx, name):
        for i in range(len(self.db.objs)):
            try:
                if self.edits[i]['config'] == idx:
                    self.edits[i]['linkname'] = str(name)
                    index = self.index(i, self.cfgcol)
                    self.dataChanged.emit(index, index)
            except:
                if self.db.objs[i]['config'] == idx:
                    self.db.objs[i]['linkname'] = str(name)
                    index = self.index(i, self.cfgcol)
                    self.dataChanged.emit(index, index)

    def rowIsChanged(self, table, index):
        (idx, f) = self.index2db(index)
        try:
            e = self.edits[idx]
            return True
        except:
            return False

    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new object", self.create)
        menu.addAction("Delete", self.delete)
        menu.addAction("Commit this object", self.commitone, self.rowIsChanged)
        menu.addAction("Commit all", self.commitall, lambda table, index: self.edits != {})
        menu.addAction("Change configuration", self.chparent, lambda table, index: index.column() == self.cfgcol)
        table.addContextMenu(menu)

        colmgr.addColumnManagerMenu(table)

    def create(self, table, index):
        pass

    def delete(self, table, index):
        pass

    def commitone(self, table, index):
        pass

    def commitall(self, table, index):
        pass

    def chparent(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.db.objs[index.row()]
        if (param.params.cfgdialog.exec_("Select new configuration for %s" % d['name'], d['config']) ==
            QtGui.QDialog.Accepted):
            self.setData(index, QtCore.QVariant(param.params.cfgdialog.result))

    # Enabled:
    #     Everything.
    # Selectable:
    #     QtCore.Qt.ItemIsSelectable
    # Editable:
    #     QtCore.Qt.ItemIsEditable
    # Drag/Drop:
    #     QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled
    #
    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.isValid():
            row = index.row()
            col = index.column()
            if col < self.coff:
                if col != self.cfgcol and col != self.statcol:
                    flags = flags | QtCore.Qt.ItemIsEditable
            else:
                if self.db.objflds[col-self.coff]['obj']:
                    flags = flags | QtCore.Qt.ItemIsEditable
        return flags

    #
    # Drag/Drop stuff.
    #
    # The "application/pmgr" mime type encodes the source position (row, col).
    #

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def mimeTypes(self):
        return ["application/pmgr"]

    def mimeData(self, indexes):
        md = QtCore.QMimeData()
        ba = QtCore.QByteArray()
        ds = QtCore.QDataStream(ba, QtCore.QIODevice.WriteOnly)
        ds << QtCore.QString("%d %d" % (indexes[0].row(), indexes[0].column()))
        md.setData("application/pmgr", ba)
        return md

    def dropMimeData(self, data, action, row, column, parent):
        if action == QtCore.Qt.IgnoreAction:
            return True
        if not data.hasFormat("application/pmgr"):
            return False
        if not parent.isValid():
            return False
        
        ba = data.data("application/pmgr")
        ds = QtCore.QDataStream(ba, QtCore.QIODevice.ReadOnly)

        text = QtCore.QString()
        ds >> text
        source = [int(l) for l in str(text).split()]
        # source[0] = from row, source[1] = from column
        # return True if the drop succeeds!
        return False
