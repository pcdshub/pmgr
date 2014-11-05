from PyQt4 import QtGui, QtCore
import param

class CfgModel(QtGui.QStandardItemModel):
    cname = ["Name", "Parent"]
    cfld  = ["name", "linkname"]
    coff  = len(cname)
    
    def __init__(self, db, ui):
        QtGui.QStandardItemModel.__init__(self)
        self.db = db
        self.ui = ui
        self.curidx = 0
        self.path = []
        self.children = []
        self.connect(ui.treeWidget, QtCore.SIGNAL("currentItemChanged(QTreeWidgetItem *, QTreeWidgetItem *)"),
                     self.treeNavigation)
        self.connect(ui.treeWidget, QtCore.SIGNAL("itemCollapsed(QTreeWidgetItem *)"),
                     self.treeCollapse)
        self.connect(ui.treeWidget, QtCore.SIGNAL("itemExpanded(QTreeWidgetItem *)"),
                     self.treeExpand)
        # Setup headers
        self.setColumnCount(2 + self.db.cfgfldcnt)
        font = QtGui.QFont()
        font.setBold(True)
        for c in range(self.db.cfgfldcnt + 2):
            if c < self.coff:
                self.setHorizontalHeaderItem(c, QtGui.QStandardItem(self.cname[c]))
            else:
                self.setHorizontalHeaderItem(c, QtGui.QStandardItem(self.db.cfgflds[c-self.coff]['alias']))
        self.is_expanded = {}
        self.buildtree()
        try:
            self.ui.treeWidget.setCurrentItem(self.tree[self.curidx]['item'])
        except:
            self.setCurIdx(0)

    def cfgchange(self):
        print "CfgModel has change!"
        self.buildtree()
        try:
            self.ui.treeWidget.setCurrentItem(self.tree[self.curidx]['item'])
        except:
            self.setCurIdx(0)

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
            try:
                # Everything defaults to collapsed!
                if self.is_expanded[id]:
                    tree.expandItem(item)
            except:
                self.is_expanded[id] = False
            r[len(r):] = t[id]['children']
        self.tree = t

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if (role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole and
            role != QtCore.Qt.ForegroundRole):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return QtCore.QVariant()
        r = index.row()
        c = index.column()
        if r < len(self.path):
            idx = self.path[r]
        else:
            idx = self.children[r - len(self.path)]
        d = self.db.getCfg(idx)
        if c < self.coff:
            if role == QtCore.Qt.ForegroundRole:
                # MCB - Could be red if changed by user!
                return QtCore.QVariant(param.params.black)
            else:
                return QtCore.QVariant(d[self.cfld[c]])
        else:
            f = self.db.cfgflds[c-self.coff]['fld'] 
            if role == QtCore.Qt.ForegroundRole:
                # MCB - Could be red if changed by user!
                color = param.params.black if f in d['vfld'] else param.params.blue
                return QtCore.QVariant(color)
            else:
                return QtCore.QVariant(d[f])
            
    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole:
            return QtGui.QStandardItemModel.setData(self, index, value, role)
        return QtGui.QStandardItemModel.setData(self, index, value, role)

    def setCurIdx(self, idx):
        self.curidx = idx
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        children = self.tree[idx]['children']
        path = [idx];
        while self.tree[idx]['link'] != None:
            idx = self.tree[idx]['link']
            path[:0] = [idx]
        self.setRowCount(len(path) + len(children))
        self.path = path
        self.children = children
        self.emit(QtCore.SIGNAL("layoutChanged()"))
        self.ui.configTable.resizeColumnsToContents()
        
    def treeNavigation(self, cur, prev):
        if cur != None:
            print "Current is %s (%d)" % (cur.text(0), cur.id)
            self.setCurIdx(cur.id)

    def treeCollapse(self, item):
        if item != None:
            self.is_expanded[item.id] = False

    def treeExpand(self, item):
        if item != None:
            self.is_expanded[item.id] = True

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
        flags = (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |
                 QtCore.Qt.ItemIsEditable)
        if index.isValid():
            row = index.row()
            col = index.column()
        return flags
