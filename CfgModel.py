from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr
import sys

class CfgModel(QtGui.QStandardItemModel):
    newname = QtCore.pyqtSignal(int, QtCore.QString)
    cname   = ["Status", "Name", "Parent"]
    cfld    = ["status", "name", "linkname"]
    coff    = len(cname)
    statcol = 0
    namecol = 1
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
        self.id2cfg = {}
        self.nextid = -1
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
        self.ui.treeWidget.expandItem(self.tree[self.curidx]['item'])
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

    def haveNewName(self, idx, name):
        for r in range(len(self.path) + len(self.children)):
            if r < len(self.path):
                i = self.path[r]
            else:
                i = self.children[r - len(self.path)]
            try:
                if self.edits[i]['link'] == idx:
                    self.edits[i]['linkname'] = str(name)
                    index = self.index(r, self.cfgcol)
                    self.dataChanged.emit(index, index)
            except:
                if self.db.id2cfg[i]['link'] == idx:
                    self.db.id2cfg[i]['linkname'] = str(name)
                    index = self.index(r, self.cfgcol)
                    self.dataChanged.emit(index, index)
        for (id, d) in self.tree.items():
            if id == idx:
                d['name'] = name
                d['item'].setText(0, name)

    def buildtree(self):
        t = {}
        for d in self.db.cfgs:
            t[d['id']] = {'name': d['name'], 'link': d['link'], 'children' : []}
        for d in self.id2cfg.values():
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

    def getCfg(self, idx):
        if idx == None:
            return {}
        if idx >= 0:
            d = self.db.id2cfg[idx]
        else:
            d = self.id2cfg[idx]
        try:
            e = self.edits[idx].keys()
        except:
            e = []
        # _color is a map from field name to color!
        if not '_color' in d.keys():
            color = {}
            haveval = {}
            editval = {}
            if d['link'] != None:
                vals = self.getCfg(d['link'])
                pcolor = vals['_color']
            for (k, v) in d.items():
                if k[:3] != 'PV_' and k[:4] != 'FLD_' and not k in self.cfld:
                    continue
                editval[k] = None
                if v == None:
                    haveval[k] = False
                    d[k] = vals[k]
                    if pcolor[k] == param.params.red or pcolor[k] == param.params.purple:
                        color[k] = param.params.purple
                    else:
                        color[k] = param.params.blue
                else:
                    haveval[k] = True
                    color[k] = param.params.black
                if k in e:
                    color[k] = param.params.red
            d['_color'] = color
            d['_val'] = haveval
            d['_editval'] = editval
        return d

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if (role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole and
            role != QtCore.Qt.ForegroundRole):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return QtCore.QVariant()
        (idx, f) = self.index2db(index)
        d = self.getCfg(idx)
        if role == QtCore.Qt.ForegroundRole:
            color = d['_color'][f]
            return QtCore.QVariant(color)
        try:
            v = self.edits[idx][f]
            return QtCore.QVariant(v)
        except:
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
        # Get all the edits for this config.
        try:
            e = self.edits[idx]
        except:
            e = {}
        hadedit = (e != {})
        # OK, the link/linkname thing is slightly weird.  The field name for our index is
        # 'linkname', but we are passing an int that should go to 'link'.  So we need to
        # change *both*!
        if f == 'linkname':
            vlink = v
            v = self.db.id2name[vlink]
        # Remove the old edit of this field, if any.
        try:
            del e[f]
            if f == 'linkname':
                del e['link']
        except:
            pass
        # Get the configured values.
        d = self.getCfg(idx)
        if not param.equal(v, d[f]):
            # If we have a change, set it as an edit.
            chg = True
            e[f] = v
            if f == 'linkname':
                e['link'] = vlink
            if not hadedit:
                # If we didn't have any changes before, we do now!
                d['status'] = "".join(sorted("M" + d['status']))
                statidx = self.index(index.row(), self.statcol)
                self.dataChanged.emit(statidx, statidx)
        else:
            chg = False
            # No change?
            if hadedit and e == {}:
                # If we deleted our last change, we're not modified any more!
                d['status'] = d['status'].replace("M", "")
                statidx = self.index(index.row(), self.statcol)
                self.dataChanged.emit(statidx, statidx)
        # Save the edits for this id!
        if e != {}:
            self.edits[idx] = e
        else:
            try:
                del self.edits[idx]
            except:
                pass
        # Set our color.
        if chg:
            d['_color'][f] = param.params.red
            chcolor = param.params.purple
        else:
            haveval = d['_editval'][f]
            if haveval == None:
                haveval = d['_val'][f]
            if haveval:
                d['_color'][f] = param.params.black
                chcolor = param.params.blue
            else:
                p = self.getCfg(d['link'])
                col = p['_color'][f]
                if col == param.params.black or col == param.params.blue:
                    d['_color'][f] = param.params.blue
                    chcolor = param.params.blue
                else:
                    d['_color'][f] = param.params.purple
                    chcolor = param.params.purple
        self.dataChanged.emit(index, index)
        # If we changed the name, let everyone know!
        if index.column() == self.namecol:
            self.db.nameedits[idx] = v
            self.db.id2name[idx] = v
            self.newname.emit(idx, v)
        # Now, fix up the children that inherit from us!
        self.fixChildren(idx, f, index.column(), v, chcolor)
        return True

    def fixChildren(self, idx, f, column, v, chcolor):
        for c in self.tree[idx]['children']:
            cd = self.getCfg(c)
            haveval = cd['_editval'][f]
            if haveval == None:
                haveval = cd['_val'][f]
            if haveval:
                continue                  # This child has a value, so he's OK!
            if not param.equal(v, cd[f]):
                cd[f] = v
                cd['_color'][f] = chcolor
                if c in self.path:
                    r = self.path.index(c)
                    index = self.index(r, column)
                    self.dataChanged.emit(index, index)
                elif c in self.children:
                    r = self.children.index(c) + len(self.path)
                    index = self.index(r, column)
                    self.dataChanged.emit(index, index)
                self.fixChildren(c, f, column, v, chcolor)
        
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

    def hasValue(self, table, index):
        (idx, f) = self.index2db(index)
        return self.getCfg(idx)['_val'][f]

    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new child", self.create)
        menu.addAction("Clone existing", self.clone)
        menu.addAction("Clone values", self.clonevals)
        menu.addAction("Delete value", self.deleteval, self.hasValue)
        menu.addAction("Create value", self.createval, lambda t, i: not self.hasValue(t, i))
        menu.addAction("Delete config", self.deletecfg)
        menu.addAction("Commit this config", self.commitone, self.rowIsChanged)
        menu.addAction("Commit all", self.commitall, lambda table, index: self.edits != {})
        menu.addAction("Change parent", self.chparent, lambda table, index: index.column() == self.cfgcol)
        table.addContextMenu(menu)

        colmgr.addColumnManagerMenu(table)

    def create(self, table, index):
        (idx, f) = self.index2db(index)
        print "Create child of %s (%d)" % (self.db.id2name[idx], idx)
        pass

    def deletecfg(self, table, index):
        pass

    def deleteval(self, table, index):
        pass

    def createval(self, table, index):
        pass

    def clone(self, table, index):
        (idx, f) = self.index2db(index)
        print "Create sibling of %s (%d)" % (self.db.id2name[idx], idx)
        l = self.getCfg(idx)['link']
        print "New parent is %s (%d)" % (self.db.id2name[l], l)

    def clonevals(self, table, index):
        pass

    def commitone(self, table, index):
        pass

    def commitall(self, table, index):
        pass

    def chparent(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.getCfg(idx)
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
