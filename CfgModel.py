from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr

class CfgModel(QtGui.QStandardItemModel):
    cname   = ["Status", "Name", "Parent"]
    cfld    = ["status", "name", "linkname"]
    coff    = len(cname)
    statcol = 0
    cfgcol  = 2
    mutable = 2
    
    def __init__(self, db, ui):
        QtGui.QStandardItemModel.__init__(self)
        self.db = db
        self.ui = ui
        self.curidx = 0
        self.path = []
        self.children = []
        self.edits = {}
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
        self.setHeaderData(self.statcol, QtCore.Qt.Horizontal,
                           QtCore.QVariant("M = Modified"),
                           QtCore.Qt.ToolTipRole)

    def cfgchange(self):
        print "CfgModel has change!"
        self.buildtree()
        try:
            self.ui.treeWidget.setCurrentItem(self.tree[self.curidx]['item'])
        except:
            self.setCurIdx(0)

    def buildtree(self):
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
        self.root = r
        self.tree = t
        self.setupTree(self.ui.treeWidget, 'item')

    def setupTree(self, tree, fld):
        tree.clear()
        r = list(self.root)  # Make a copy!
        t = self.tree
        for id in r:
            if t[id]['link'] == None:
                item = QtGui.QTreeWidgetItem(tree)
            else:
                item = QtGui.QTreeWidgetItem()
            item.id = id
            item.setText(0, t[id]['name'])
            t[id][fld] = item
            parent = t[id]['link']
            if parent != None:
                t[parent][fld].addChild(item)
            try:
                # Everything defaults to collapsed!
                if self.is_expanded[id]:
                    tree.expandItem(item)
            except:
                self.is_expanded[id] = False
            r[len(r):] = t[id]['children']
        return t

    def index2db(self, index):
        r = index.row()
        c = index.column()
        if r < len(self.path):
            idx = self.path[r]
        else:
            idx = self.children[r - len(self.path)]
        if c < self.coff:
            f = self.cfld[c]
        else:
            f = self.db.cfgflds[c-self.coff]['fld']
        return (idx, f)

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if (role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole and
            role != QtCore.Qt.ForegroundRole):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return QtCore.QVariant()
        (idx, f) = self.index2db(index)
        d = self.db.getCfg(idx)
        try:
            v = self.edits[idx][f]
            if role == QtCore.Qt.ForegroundRole:
                return QtCore.QVariant(param.params.red)
            else:
                return QtCore.QVariant(v)
        except:
            if role == QtCore.Qt.ForegroundRole:
                # MCB - Could be red if changed by user!
                color = param.params.blue if f in d['vfld'] else param.params.black
                return QtCore.QVariant(color)
            else:
                return QtCore.QVariant(d[f])
            
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
        # OK, the link/linkname thing is slightly weird.  The field name for our index is
        # 'linkname', but we are passing an int that should go to 'link'.  So we need to
        # change *both*!
        if f == 'linkname':
            vlink = v
            v = self.db.id2cfg[vlink]['name']
        try:
            del d[f]
            if f == 'linkname':
                del d['link']
        except:
            pass
        dd = self.db.getCfg(idx)
        if not param.equal(v, dd[f]):
            d[f] = v
            if f == 'linkname':
                d['link'] = vlink
            if not hadedit:
                dd['status'] = "".join(sorted("M" + dd['status']))
                statidx = self.index(index.row(), self.statcol)
                self.dataChanged.emit(index, index)
        else:
            if hadedit and d == {}:
                dd['status'] = dd['status'].replace("M", "")
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

    def rowIsChanged(self, table, index):
        (idx, f) = self.index2db(index)
        try:
            e = self.edits[idx]
            return True
        except:
            return False

    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new", self.create)
        menu.addAction("Clone existing", self.clone)
        menu.addAction("Clone values", self.clonevals)
        menu.addAction("Delete", self.delete)
        menu.addAction("Commit this config", self.commitone, self.rowIsChanged)
        menu.addAction("Commit all", self.commitall, lambda table, index: self.edits != {})
        menu.addAction("Change parent", self.chparent, lambda table, index: index.column() == self.cfgcol)
        table.addContextMenu(menu)

        colmgr.addColumnManagerMenu(table)

    def create(self, table, index):
        pass

    def delete(self, table, index):
        pass

    def clone(self, table, index):
        pass

    def clonevals(self, table, index):
        pass

    def commitone(self, table, index):
        pass

    def commitall(self, table, index):
        pass

    def chparent(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.db.getCfg(idx)
        if (param.params.cfgdialog.exec_("Select new parent for %s" % d['name'], d['link']) ==
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
            if col != self.cfgcol and col != self.statcol:
                flags = flags | QtCore.Qt.ItemIsEditable
        return flags
