from PyQt4 import QtGui, QtCore
import param

class ObjModel(QtGui.QStandardItemModel):
    cname = ["Name", "Config", "PV Base"]
    cfld  = ["name", "linkname", "rec_base"]
    coff  = len(cname)
    
    def __init__(self, db, ui):
        QtGui.QStandardItemModel.__init__(self)
        self.db = db
        self.ui = ui
        self.id2idx = None
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

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if (role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole and
            role != QtCore.Qt.ForegroundRole):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return QtCore.QVariant()
        try:
            r = index.row()
            d = self.db.objs[r]
            c = index.column()
            if c < self.coff:
                if role == QtCore.Qt.ForegroundRole:
                    # MCB - Could be red if changed by user!
                    return QtCore.QVariant(param.params.black)
                else:
                    return QtCore.QVariant(d[self.cfld[c]])
            else:
                f = self.db.objflds[c-self.coff]['fld']
                v = d['curval'][f]
                if role == QtCore.Qt.ForegroundRole:
                    if self.db.objflds[c-self.coff]['obj']:
                        v2 = d[f]
                    else:
                        v2 = self.db.id2cfg[d['config']][f]
                    # MCB - Could be red if an object parameter changed by user!
                    if v == v2:
                        return QtCore.QVariant(param.params.black)
                    else:
                        return QtCore.QVariant(param.params.blue)
                else:
                    return QtCore.QVariant(v)
        except:
            return QtCore.QVariant()

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole:
            return QtGui.QStandardItemModel.setData(self, index, value, role)
        return QtGui.QStandardItemModel.setData(self, index, value, role)
        
    def value(self, entry, c, display=True):
        if c < self.coff:
            return entry[self.cfld[c]]
        else:
            return entry[self.db.objflds[c-self.coff]['fld']]

    def sort(self, Ncol, order):
        self.lastsort = (Ncol, order)
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.db.objs = sorted(self.db.objs, key=lambda d: self.value(d, Ncol))
        if order == QtCore.Qt.DescendingOrder:
            self.db.objs.reverse()
        self.makeidx()
        self.emit(QtCore.SIGNAL("layoutChanged()"))
        self.ui.objectTable.resizeColumnsToContents()

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
        self.ui.objectTable.resizeColumnsToContents()

    def pvchange(self, id, fldidx):
        if self.id2idx == None:
            self.makeidx()
        idx = self.index(self.id2idx[id], fldidx + self.coff)
        self.dataChanged.emit(idx, idx)

"""
    # Enabled:
    #     Everything.
    # Editable:
    #     Any main row.
    #     Any detector column (col >= firstdetidx)
    # Drag/Drop:
    #     Any detector column header (row == 0 and col >= firstdetidx)
    #     Any timing class header (col == 0 and row != 0)
    #
    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled
        if index.isValid():
            row = index.row()
            col = index.column()
            if self.isMainRow(row) or col >= param.params.firstdetidx:
                flags = flags | QtCore.Qt.ItemIsEditable
            if ((row == 0 and col >= param.params.firstdetidx) or
                (col == 0 and row != 0)):
                flags = (flags | QtCore.Qt.ItemIsSelectable |
                         QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled)
        return flags
        
    def setupHeaders(self):
        for i in range(param.params.firstdetidx):
            idx = self.index(0, i)
            self.setData(idx, QtCore.QVariant(param.params.colheaders[i]))
            self.setData(idx, QtCore.QVariant(QtCore.Qt.AlignBottom|QtCore.Qt.AlignHCenter),
                         QtCore.Qt.TextAlignmentRole)

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
        md.setData("application/trigtool", ba)
        return md

    def dropMimeData(self, data, action, row, column, parent):
        if action == QtCore.Qt.IgnoreAction:
            return True
        if not data.hasFormat("application/trigtool"):
            return False
        if not parent.isValid():
            return False
        
        ba = data.data("application/pmgr")
        ds = QtCore.QDataStream(ba, QtCore.QIODevice.ReadOnly)

        text = QtCore.QString()
        ds >> text
        source = [int(l) for l in str(text).split()]
"""
