from PyQt4 import QtGui, QtCore
import param

class ObjModel(QtGui.QStandardItemModel):
    def __init__(self, db):
        row = 1
        col = 2
        QtGui.QStandardItemModel.__init__(self, row, col)
        self.db = db
        # Setup headers
        self.setColumnCount(2 + self.db.objfldcnt)
        self.setRowCount(1)
        font = QtGui.QFont()
        font.setBold(True)
        for c in range(self.db.objfldcnt + 3):
            if c == 0:
                self.setData(self.index(0, 0), QtCore.QVariant("Name"), QtCore.Qt.DisplayRole)
            elif c == 1:
                self.setData(self.index(0, 1), QtCore.QVariant("Config"), QtCore.Qt.DisplayRole)
            elif c == 2:
                self.setData(self.index(0, 2), QtCore.QVariant("PV Base"), QtCore.Qt.DisplayRole)
            else:
                self.setData(self.index(0, c), QtCore.QVariant(self.db.objflds[c-3]['alias']),
                             QtCore.Qt.DisplayRole)
            self.setData(self.index(0, c), QtCore.QVariant(param.params.gray), QtCore.Qt.BackgroundRole)
            self.setData(self.index(0, c), QtCore.QVariant(font), QtCore.Qt.FontRole)

    def objchange(self):
        print "ObjModel has object change!"

    def cfgchange(self):
        print "ObjModel has config change!"

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
