from PyQt4 import QtGui, QtCore
import param

class CfgModel(QtGui.QStandardItemModel):
    def __init__(self, db, ui):
        QtGui.QStandardItemModel.__init__(self)
        self.db = db
        self.ui = ui
        self.curidx = 0
        self.connect(ui.treeWidget, QtCore.SIGNAL("currentItemChanged(QTreeWidgetItem *, QTreeWidgetItem *)"),
                     self.treeNavigation)
        # Setup headers
        self.setColumnCount(2 + self.db.cfgfldcnt)
        self.setRowCount(1)
        font = QtGui.QFont()
        font.setBold(True)
        for c in range(self.db.cfgfldcnt + 2):
            if c == 0:
                self.setData(self.index(0, 0), QtCore.QVariant("Name"), QtCore.Qt.DisplayRole)
            elif c == 1:
                self.setData(self.index(0, 1), QtCore.QVariant("Parent"), QtCore.Qt.DisplayRole)
            else:
                self.setData(self.index(0, c), QtCore.QVariant(self.db.cfgflds[c-2]['alias']),
                             QtCore.Qt.DisplayRole)
            self.setData(self.index(0, c), QtCore.QVariant(param.params.gray), QtCore.Qt.BackgroundRole)
            self.setData(self.index(0, c), QtCore.QVariant(font), QtCore.Qt.FontRole)
        self.buildtree()
        self.setCurIdx(0)

    def cfgchange(self):
        print "CfgModel has change!"
        self.buildtree()
        self.setCurIdx(self.curidx)

    def buildtree(self):
        tree = self.ui.treeWidget
        t = {}
        for d in self.db.cfgs:
            t[d['id']] = {'name': d['name'], 'link': d['link'], 'children' : []}
        r = []
        for (k, v) in t.items():
            l = v['link']
            if l == None:
                r.append(k)
            else:
                t[l]['children'].append(k)
        r.sort(key=lambda v: t[v]['name'])
        for d in t.values():
            d['children'].sort(key=lambda v: t[v]['name'])
        tree.clear()
        for id in r:
            if t[id]['link'] == None:
                item = QtGui.QTreeWidgetItem(tree)
            else:
                item = QtGui.QTreeWidgetItem()
            item.id = id
            item.setText(0, t[id]['name'])
            t[id]['item'] = item
            parent = t[id]['link']
            if parent != None:
                t[parent]['item'].addChild(item)
            r[len(r):] = t[id]['children']
        self.tree = t

    def setCurIdx(self, idx):
        self.curidx = idx
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        children = self.tree[idx]['children']
        path = [idx];
        while self.tree[idx]['link'] != None:
            idx = self.tree[idx]['link']
            path[:0] = [idx]
        self.setRowCount(1 + len(path) + len(children))
        vals = {}
        for i in range(len(path)):
            idx = path[i]
            d = self.db.id2cfg[idx]
            if not 'vfld' in d.keys():
                vfld = []
                for (k, v) in d.items():
                    if k[:3] != 'PV_' and k[:4] != 'FLD_':
                        continue
                    if v == None:
                        d[k] = vals[k]
                    else:
                        vfld.append(k)
                d['vfld'] = vfld
            else:
                vfld = d['vfld']
            for c in range(self.db.cfgfldcnt + 2):
                didx = self.index(i+1, c)
                if c == 0:
                    self.setData(didx, QtCore.QVariant(d['name']), QtCore.Qt.DisplayRole)
                elif c == 1:
                    link = d['link']
                    if link == None:
                        link = ""
                    else:
                        link = self.db.id2cfg[link]['name']
                    self.setData(didx, QtCore.QVariant(link), QtCore.Qt.DisplayRole)
                else:
                    f = self.db.cfgflds[c-2]['fld'] 
                    color = param.params.black if f in vfld else param.params.blue
                    self.setData(didx, QtCore.QVariant(d[f]), QtCore.Qt.DisplayRole)
                    self.setData(didx, QtCore.QVariant(color), QtCore.Qt.ForegroundRole)
            vals = d
        off = len(path) + 1
        for i in range(len(children)):
            idx = children[i]
            d = self.db.id2cfg[idx]
            if not 'vfld' in d.keys():
                vfld = []
                for (k, v) in d.items():
                    if v == None:
                        d[k] = vals[k]
                    else:
                        vfld.append(k)
                d['vfld'] = vfld
            else:
                vfld = d['vfld']
            for c in range(self.db.cfgfldcnt + 2):
                didx = self.index(i+off, c)
                if c == 0:
                    self.setData(didx, QtCore.QVariant(d['name']), QtCore.Qt.DisplayRole)
                elif c == 1:
                    link = d['link']
                    if link == None:
                        link = ""
                    else:
                        link = self.db.id2cfg[link]['name']
                    self.setData(didx, QtCore.QVariant(link), QtCore.Qt.DisplayRole)
                else:
                    f = self.db.cfgflds[c-2]['fld'] 
                    color = param.params.black if f in vfld else param.params.blue
                    self.setData(didx, QtCore.QVariant(d[f]), QtCore.Qt.DisplayRole)
                    self.setData(didx, QtCore.QVariant(color), QtCore.Qt.ForegroundRole)
        self.emit(QtCore.SIGNAL("layoutChanged()"))
        self.ui.configTable.resizeColumnsToContents()
        
    def treeNavigation(self, cur, prev):
        if cur != None:
            print "Current is %s (%d)" % (cur.text(0), cur.id)
            self.setCurIdx(cur.id)

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
