from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr
import sys
import datetime

class CfgModel(QtGui.QStandardItemModel):
    newname = QtCore.pyqtSignal(int, QtCore.QString)
    cfgChanged = QtCore.pyqtSignal(int, QtCore.QString)
    
    cname   = ["Status", "Name", "Parent"]
    cfld    = ["status", "name", "cfgname"]
    coff    = len(cname)
    statcol = 0
    namecol = 1
    cfgcol  = 2
    mutable = 2   # The first non-frozen column
    
    def __init__(self, db, ui):
        QtGui.QStandardItemModel.__init__(self)
        self.db = db
        self.ui = ui
        self.curidx = 0
        self.path = []
        self.edits = {}
        self.editval = {}
        self.cfgs = {}
        self.nextid = -1
        self.connect(ui.treeWidget, QtCore.SIGNAL("currentItemChanged(QTreeWidgetItem *, QTreeWidgetItem *)"),
                     self.treeNavigation)
        self.connect(ui.treeWidget, QtCore.SIGNAL("itemCollapsed(QTreeWidgetItem *)"),
                     self.treeCollapse)
        self.connect(ui.treeWidget, QtCore.SIGNAL("itemExpanded(QTreeWidgetItem *)"),
                     self.treeExpand)
        # Setup headers
        self.colcnt = self.db.cfgfldcnt + self.coff
        self.setColumnCount(self.colcnt)
        font = QtGui.QFont()
        font.setBold(True)
        for c in range(self.colcnt):
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
                           QtCore.QVariant("D = Deleted\nM = Modified\nN = New"),
                           QtCore.Qt.ToolTipRole)

    def cfgchange(self):
        print "CfgModel has changed!"
        self.buildtree()
        try:
            self.ui.treeWidget.setCurrentItem(self.tree[self.curidx]['item'])
        except:
            self.setCurIdx(0)

    def setModifiedStatus(self, index, idx, d):
        try:
            v = d['status'].index("M")
            wasmod = True
        except:
            wasmod = False
        mod = False
        if self.editval[idx] != {}:
            mod = True
        try:
            if self.edits[idx] != {}:
                mod = True
        except:
            pass
        if mod != wasmod:
            if mod:
                d['status'] = "".join(sorted("M" + d['status']))
            else:
                d['status'] = d['status'].replace("M", "")
            statidx = self.index(index.row(), self.statcol)
            self.dataChanged.emit(statidx, statidx)
    
    def haveNewName(self, idx, name):
        name = str(name)
        utils.fixName(self.db.cfgs.values(), idx, name)
        utils.fixName(self.cfgs.values(), idx, name)
        utils.fixName(self.edits.values(), idx, name)
        for r in range(len(self.path)):
            i = self.path[r]
            try:
                if self.edits[i]['config'] == idx:
                    index = self.index(r, self.cfgcol)
                    self.dataChanged.emit(index, index)
            except:
                if i >= 0:
                    d = self.db.cfgs[i]
                else:
                    d = self.cfgs[i]
                if d['config'] == idx:
                    index = self.index(r, self.cfgcol)
                    self.dataChanged.emit(index, index)
        for (id, d) in self.tree.items():
            if id == idx:
                d['name'] = name
                d['item'].setText(0, name)

    def buildtree(self):
        t = {}
        for d in self.db.cfgs.values():
            idx = d['id']
            t[idx] = {'name': d['name'], 'link': d['config'], 'children' : []}
            try:
                t[idx]['link'] = self.edits[idx]['link']
            except:
                pass
        for d in self.cfgs.values():
            idx = d['id']
            t[idx] = {'name': d['name'], 'link': d['config'], 'children' : []}
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
        idx = self.path[r]
        if c < self.coff:
            f = self.cfld[c]
        else:
            f = self.db.cfgflds[c-self.coff]['fld']
        return (idx, f)

    def getCfg(self, idx):
        if idx == None:
            return {}
        if idx >= 0:
            d = self.db.cfgs[idx]
        else:
            d = self.cfgs[idx]
        try:
            e = self.edits[idx].keys()
        except:
            e = []
        # _color is a map from field name to color!
        if not '_color' in d.keys():
            color = {}
            haveval = {}
            if d['config'] != None:
                vals = self.getCfg(d['config'])
                pcolor = vals['_color']
            for (k, v) in d.items():
                if k[:3] != 'PV_' and k[:4] != 'FLD_' and not k in self.cfld:
                    continue
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
            self.editval[idx] = {}
        return d

    def geteditval(self, idx, f):
        try:
            return self.editval[idx][f]
        except:
            return None

    def seteditval(self, idx, f, v):
        if idx < 0:
            self.cfgs[idx][f] = v
            return
        else:
            if v == None:
                try:
                    del self.editval[idx][f]
                except:
                    pass
            else:
                try:
                    self.editval[idx][f] = v
                except:
                    self.editval[idx] = {f: v}

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
        # OK, the config/cfgname thing is slightly weird.  The field name for our index is
        # 'cfgname', but we are passing an int that should go to 'config'.  So we need to
        # change *both*!
        if f == 'cfgname':
            vlink = v
            v = self.db.getCfgName(vlink)
        # Remove the old edit of this field, if any.
        try:
            del e[f]
            if f == 'cfgname':
                del e['config']
        except:
            pass
        # Get the configured values.
        d = self.getCfg(idx)
        if not param.equal(v, d[f]):
            # If we have a change, set it as an edit.
            chg = True
            e[f] = v
            if f == 'cfgname':
                e['config'] = vlink
        else:
            chg = False
            # No change?
        # Save the edits for this id!
        if e != {}:
            if idx < 0:
                self.cfgs[idx].update(e)
            else:
                self.edits[idx] = e
        else:
            try:
                del self.edits[idx]
            except:
                pass
        self.setModifiedStatus(index, idx, d)
        # Set our color.
        if chg and idx >= 0:
            # Only mark changes to *existing* configurations in red!
            d['_color'][f] = param.params.red
            chcolor = param.params.purple
        elif self.geteditval(idx, f) != None:
            d['_color'][f] = param.params.red
            chcolor = param.params.purple
        else:
            if d['_val'][f]:
                d['_color'][f] = param.params.black
                chcolor = param.params.blue
            else:
                p = self.getCfg(d['config'])
                col = p['_color'][f]
                if col == param.params.black or col == param.params.blue:
                    d['_color'][f] = param.params.blue
                    chcolor = param.params.blue
                else:
                    d['_color'][f] = param.params.purple
                    chcolor = param.params.purple
        self.dataChanged.emit(index, index)
        if index.column() == self.namecol:
            self.db.setCfgName(idx, v)
            self.newname.emit(idx, v)
        else:
            self.cfgChanged.emit(idx, f)
        # Now, fix up the children that inherit from us!
        self.fixChildren(idx, f, index.column(), v, chcolor)
        return True

    def fixChildren(self, idx, f, column, v, chcolor):
        for c in self.tree[idx]['children']:
            cd = self.getCfg(c)
            haveval = self.geteditval(c, f)
            if haveval == None:
                haveval = cd['_val'][f]
            if haveval:
                continue                  # This child has a value, so he's OK!
            if not param.equal(v, cd[f]):
                cd[f] = v
                if idx < 0 and c >= 0:
                    # If we inherit from a *new* config, we are purple!
                    cd['_color'][f] = param.params.purple
                elif idx < 0 and chcolor == param.params.purple:
                    # On the other hand, if we *are* a new config, we can't be purple!
                    cd['_color'][f] = param.params.blue
                else:
                    cd['_color'][f] = chcolor
                self.cfgChanged.emit(c, f)
                if c in self.path:
                    r = self.path.index(c)
                    index = self.index(r, column)
                    self.dataChanged.emit(index, index)
                self.fixChildren(c, f, column, v, cd['_color'][f])
        
    def setCurIdx(self, idx):
        self.curidx = idx
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        children = self.tree[idx]['children']
        path = [idx];
        while self.tree[idx]['link'] != None:
            idx = self.tree[idx]['link']
            path[:0] = [idx]
        path[len(path):] = children
        self.path = path
        self.setRowCount(len(path))
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

    def hasValue(self, v, table, index):
        if index.column() < self.coff:  # These values just aren't deleteable!
            return False
        (idx, f) = self.index2db(index)
        d = self.getCfg(idx)
        ev = self.geteditval(idx, f)
        if ev != None:
            return ev == v
        return d['_val'][f] == v

    def checkStatus(self, index, vals):
        (idx, f) = self.index2db(index)
        s = self.getCfg(idx)['status']
        for v in vals:
            if v in s:
                return True
        return False

    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new child", self.createnew)
        menu.addAction("Clone existing", self.clone)
        menu.addAction("Clone values", self.clonevals)
        menu.addAction("Change parent", self.chparent, lambda table, index: index.column() == self.cfgcol)
        menu.addAction("Delete value", self.deleteval, lambda t, i: self.hasValue(True, t, i))
        menu.addAction("Create value", self.createval, lambda t, i: self.hasValue(False, t, i))
        menu.addAction("Delete config", self.deletecfg, lambda table, index: not self.checkStatus(index, 'D'))
        menu.addAction("Undelete config", self.undeletecfg, lambda table, index: self.checkStatus(index, 'D'))
        menu.addAction("Commit this config", self.commitone, lambda table, index: self.checkStatus(index, 'DMN'))
        table.addContextMenu(menu)

        colmgr.addColumnManagerMenu(table)

    def create_child(self, parent, sibling=None, useval=False):
        id = self.nextid;
        self.nextid -= 1
        now = datetime.datetime.now()
        d = {'status': "N", 'name': "NewConfig%d" % id, 'config': parent,
             'cfgname': self.db.getCfgName(parent), 'id': id, 'owner': None,
             'security': None, 'dt_created': now, 'dt_updated': now}
        if sibling == None:
            vals = self.getCfg(parent)
        else:
            vals = self.getCfg(sibling)
        color = {}
        haveval = {}
        for f in self.db.cfgflds:
            fld = f['fld']
            d[fld] = vals[fld]
            if sibling == None:
                color[fld] = param.params.blue
                haveval[fld] = False
            elif useval:
                color[fld] = param.params.black
                haveval[fld] = True
            else:
                v = vals['_val'][fld]
                haveval[fld] = v
                if v:
                    color[fld] = param.params.black
                else:
                    color[fld] = vals['_color'][fld]
        for fld in self.cfld:
            color[fld] = param.params.black
        d['_color'] = color
        d['_val'] = haveval
        self.editval[id] = {}
        self.cfgs[id] = d
        self.buildtree()
        self.setCurIdx(id)
        return id

    def createnew(self, table, index):
        (idx, f) = self.index2db(index)
        id = self.create_child(idx)

    def clone(self, table, index):
        (idx, f) = self.index2db(index)
        parent = self.getCfg(idx)['config']
        id = self.create_child(parent, idx)

    def clonevals(self, table, index):
        (idx, f) = self.index2db(index)
        parent = self.getCfg(idx)['config']
        id = self.create_child(parent, idx, True)

    def deleteval(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.getCfg(idx)
        pidx = d['config']
        if pidx != None:                     # Can't delete a value from a root class!
            p = self.getCfg(pidx)
            if self.geteditval(idx, f) == None:
                self.seteditval(idx, f, False)
            else:
                self.seteditval(idx, f, None)
            self.setModifiedStatus(index, idx, d)
            if idx < 0:
                d['_color'][f] = param.params.blue
            elif self.geteditval(idx, f) != None:
                d['_color'][f] = param.params.red
            else:
                try:
                    v = self.edits[idx][f]
                    d['_color'][f] = param.params.red
                except:
                    pcolor = p['_color'][f]
                    if pcolor == param.params.red or pcolor == param.params.purple:
                        d['_color'][f] = param.params.purple
                    else:
                        d['_color'][f] = param.params.blue
            d[f] = p[f]
        self.dataChanged.emit(index, index)

    def createval(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.getCfg(idx)
        if self.geteditval(idx, f) == None:
            self.seteditval(idx, f, True)
        else:
            self.seteditval(idx, f, None)
        self.setModifiedStatus(index, idx, d)
        if idx < 0:
            d['_color'][f] = param.params.black
        elif self.geteditval(idx, f) != None:
            d['_color'][f] = param.params.red
        else:
            try:
                v = self.edits[idx][f]
                d['_color'][f] = param.params.red
            except:
                d['_color'][f] = param.params.black
        self.dataChanged.emit(index, index)

    def commitone(self, table, index):
        (idx, f) = self.index2db(index)
        print "Commit Config %d" % idx

    def deletecfg(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.getCfg(idx)
        if d['config'] != None:
            d['status'] = "".join(sorted("D" + d['status']))
            statidx = self.index(index.row(), self.statcol)
            self.dataChanged.emit(statidx, statidx)
        else:
            QtGui.QMessageBox.critical(None,
                                       "Error", "Cannot delete root configuration!",
                                       QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)

    def undeletecfg(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.getCfg(idx)
        d['status'] = d['status'].replace("D", "")
        statidx = self.index(index.row(), self.statcol)
        self.dataChanged.emit(statidx, statidx)

    def chparent(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.getCfg(idx)
        if d['config'] == None:
            QtGui.QMessageBox.critical(None,
                                 "Error", "Cannot change parent of root class!",
                                 QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
            return
        if (param.params.cfgdialog.exec_("Select new parent for %s" % d['name'], d['config']) ==
            QtGui.QDialog.Accepted):
            (idx, f) = self.index2db(index)
            p = param.params.cfgdialog.result
            while p != None:
                p = self.getCfg(p)['config']
                if p == idx:
                    QtGui.QMessageBox.critical(None,
                                               "Error", "Configuration change is circular!",
                                               QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
                    return
            self.setData(index, QtCore.QVariant(param.params.cfgdialog.result))
            p = self.getCfg(param.params.cfgdialog.result)
            pcolor = p['_color']
            d = self.getCfg(idx)
            color = d['_color']
            for (k, v) in d['_val'].items():
                if v == False:
                    d[k] = p[k]
                    try:
                        vv = self.edits[idx][k]
                        color[k] = param.params.red
                    except:
                        if pcolor[k] == param.params.red or pcolor[k] == param.params.purple:
                            color[k] = param.params.purple
                        else:
                            color[k] = param.params.blue
            self.buildtree()
            self.setCurIdx(idx)

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
