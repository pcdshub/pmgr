from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr
import sys
import datetime

class CfgModel(QtGui.QStandardItemModel):
    newname = QtCore.pyqtSignal(int, QtCore.QString)
    cfgChanged = QtCore.pyqtSignal(int, QtCore.QString)
    
    cname   = ["Status", "Name", "Parent", "Owner"]
    cfld    = ["status", "name", "cfgname", "owner"]
    ctips   = ["D = Deleted\nM = Modified\nN = New", "Configuration Name", "Parent Configuration", "Owner"]
    coff    = len(cname)
    statcol = 0
    namecol = 1
    cfgcol  = 2
    owncol  = 3
    mutable = 2   # The first non-frozen column
    fixflds = ["status", "cfgname", "owner"]
    
    def __init__(self):
        QtGui.QStandardItemModel.__init__(self)
        self.curidx = 0
        self.path = []
        self.edits = {}
        self.editval = {}
        self.cfgs = {}
        self.status = {}
        self.nextid = -1
        self.connect(param.params.ui.treeWidget,
                     QtCore.SIGNAL("currentItemChanged(QTreeWidgetItem *, QTreeWidgetItem *)"),
                     self.treeNavigation)
        self.connect(param.params.ui.treeWidget, QtCore.SIGNAL("itemCollapsed(QTreeWidgetItem *)"),
                     self.treeCollapse)
        self.connect(param.params.ui.treeWidget, QtCore.SIGNAL("itemExpanded(QTreeWidgetItem *)"),
                     self.treeExpand)
        # Setup headers
        self.colcnt = len(param.params.pobj.cfgflds) + self.coff
        self.setColumnCount(self.colcnt)
        font = QtGui.QFont()
        font.setBold(True)
        for c in range(self.colcnt):
            if c < self.coff:
                i = QtGui.QStandardItem(self.cname[c])
                i.setToolTip(self.ctips[c])
            else:
                i = QtGui.QStandardItem(param.params.pobj.cfgflds[c-self.coff]['alias'])
                desc = param.params.pobj.cfgflds[c-self.coff]['tooltip']
                if desc != "":
                    i.setToolTip(desc)
            self.setHorizontalHeaderItem(c, i)
        self.is_expanded = {}
        self.createStatus()
        self.buildtree()
        try:
            param.params.ui.treeWidget.setCurrentItem(self.tree[self.curidx]['item'])
        except:
            self.setCurIdx(0)
        param.params.ui.treeWidget.expandItem(self.tree[self.curidx]['item'])

    def createStatus(self):
        for d in param.params.pobj.cfgs.values():
            try:
                v = self.status[d['id']]
            except:
                self.status[d['id']] = ""

    def cfgchange(self):
        self.createStatus()
        self.buildtree()
        try:
            param.params.ui.treeWidget.setCurrentItem(self.tree[self.curidx]['item'])
        except:
            self.setCurIdx(0)

    def setModifiedStatus(self, index, idx, d):
        if idx < 0:
            return
        try:
            v = self.status[idx].index("M")
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
                self.status[idx] = "".join(sorted("M" + self.status[idx]))
            else:
                self.status[idx] = self.status[idx].replace("M", "")
            statidx = self.index(index.row(), self.statcol)
            self.dataChanged.emit(statidx, statidx)
    
    def haveNewName(self, idx, name):
        name = str(name)
        utils.fixName(param.params.pobj.cfgs.values(), idx, name)
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
                    d = param.params.pobj.cfgs[i]
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
        for d in param.params.pobj.cfgs.values():
            idx = d['id']
            t[idx] = {'name': d['name'], 'link': d['config'], 'children' : []}
            try:
                t[idx]['link'] = self.edits[idx]['config']
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
        #
        # Sigh.  Since other users can be changing configs out from under us,
        # we might inadvertently end up with loops.  We'll take care of this
        # before we commit, but for now, we need to make sure everything is
        # reachable.
        #
        d = list(r)
        for id in d:                         # This loop builds all of the rooted trees.
            d[len(d):] = t[id]['children']
        for (k, v) in t.items():
            if k in d:
                continue
            r.append(k)                      # If this isn't in a rooted tree, it must be in a loop!
            d.append(k)
            l = v['link']
            while l != k:
                d.append(l)
                l = t[l]['link']
        r.sort(key=lambda v: t[v]['name'])
        for d in t.values():
            d['children'].sort(key=lambda v: t[v]['name'])
        self.root = r
        self.tree = t
        self.setupTree(param.params.ui.treeWidget, 'item')

    def setupTree(self, tree, fld):
        tree.clear()
        r = list(self.root)  # Make a copy!
        t = self.tree
        d = []
        for id in r:
            if id in d:
                continue
            d.append(id)
            if id in self.root:
                item = QtGui.QTreeWidgetItem(tree)
                parent = None
            else:
                item = QtGui.QTreeWidgetItem()
                parent = t[id]['link']
            item.id = id
            item.setText(0, t[id]['name'])
            t[id][fld] = item
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
            f = param.params.pobj.cfgflds[c-self.coff]['fld']
        return (idx, f)

    def db2index(self, idx, f):
        try:
            c = param.params.pobj.fldmap[f]['cfgidx'] + self.coff
            r = self.path.index(idx)
            return self.index(r, c)
        except:
            return None

    def getCfg(self, idx, loop=[]):
        if idx == None or idx in loop:
            return {}
        if idx >= 0:
            d = param.params.pobj.cfgs[idx]
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
            try:
                v = self.edits[idx]['mutex']
            except:
                v = d['mutex']
            if d['config'] != None:
                lp = list(loop)
                lp.append(idx)
                vals = self.getCfg(d['config'], lp)
                pcolor = vals['_color']
                pmutex = vals['curmutex']
                mutex = ""
                for i in range(len(param.params.pobj.mutex_sets)):
                    if v[i] != ' ':
                        mutex += v[i]
                    else:
                        mutex += pmutex[i]
                d['curmutex'] = mutex
            else:
                d['curmutex'] = v
            for (k, v) in d.items():
                if k[:3] != 'PV_' and k[:4] != 'FLD_' and not k in self.cfld:
                    continue
                if v == None and k != "owner":
                    haveval[k] = chr(param.params.pobj.fldmap[k]['colorder']+0x40) in d['curmutex']
                    color[k] = param.params.almond
                else:
                    haveval[k] = True
                    color[k] = param.params.black
                if not haveval[k]:
                    try:
                        d[k] = vals[k]
                    except:
                        d[k] = None
                    try:
                        if pcolor[k] == param.params.red or pcolor[k] == param.params.purple:
                            color[k] = param.params.purple
                        else:
                            color[k] = param.params.blue
                    except:
                        color[k] = param.params.blue
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

    def getval(self, idx, f):
        try:
            return self.edits[idx][f]
        except:
            return self.getCfg(idx)[f]

    def seteditval(self, idx, f, v):
        if idx < 0:
            self.cfgs[idx]['_val'][f] = v
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
            role != QtCore.Qt.ForegroundRole and role != QtCore.Qt.BackgroundRole and
            role != QtCore.Qt.ToolTipRole):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return QtCore.QVariant()
        (idx, f) = self.index2db(index)
        if role == QtCore.Qt.ToolTipRole:
            # We'll make this smarter later!
            return QtGui.QStandardItemModel.data(self, index, role)
        if f == "status":
            if role == QtCore.Qt.BackgroundRole:
                return QtCore.QVariant(param.params.white)
            elif role == QtCore.Qt.ForegroundRole:
                return QtCore.QVariant(param.params.black)
            else:
                return QtCore.QVariant(self.status[idx])
        d = self.getCfg(idx)
        if role == QtCore.Qt.ForegroundRole:
            color = d['_color'][f]
            return QtCore.QVariant(color)
        elif role == QtCore.Qt.BackgroundRole:
            if f in self.cfld:
                return QtCore.QVariant(param.params.white)
            if chr(param.params.pobj.fldmap[f]['colorder']+0x40) in d['curmutex']:
                return QtCore.QVariant(param.params.almond)
            else:
                return QtCore.QVariant(param.params.white)
        else:
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
        elif t == QtCore.QMetaType.Void:
            v = None
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
            v = param.params.db.getCfgName(vlink)
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
            self.createallval(None, index)
        else:
            chg = False
            # No change?
        # Save the edits for this id!
        if e != {}:
            if idx < 0:
                self.cfgs[idx].update(e)
                for k in e.keys():
                    self.cfgs[idx]['_val'][k] = True
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
        c = index.column()
        try:
            cm = chr(param.params.pobj.fldmap[f]['colorder']+0x40)
            if (d['_color'][f] != param.params.blue and
                d['_color'][f] != param.params.purple and
                cm in d['curmutex']):
                # This is a calculated value!
                i = d['curmutex'].find(cm)
                d['curmutex'] = self.promote(idx, f, i, d['curmutex'])
        except:
            pass
        self.dataChanged.emit(index, index)
        if c == self.namecol:
            param.params.db.setCfgName(idx, v)
            self.newname.emit(idx, v)
        else:
            self.cfgChanged.emit(idx, f)
        # Now, fix up the children that inherit from us!
        self.fixChildren(idx, f, c, v, chcolor)
        return True

    #
    # This is called when we set a value on (idx, f) and this is currently
    # a calculated value.
    #
    def promote(self, idx, f, setidx, curmutex):
        cfg = self.getCfg(idx)
        mlist = param.params.pobj.mutex_sets[setidx]
        if len(mlist) == 2:
            # No need to prompt, the other has to be the derived value!
            if mlist[0] == f:
                derived = mlist[1]
            else:
                derived = mlist[0]
        else:
            d = param.params.deriveddialog
            d.reset()
            for fld in mlist:
                if fld != f:
                    d.addValue(param.params.pobj.fldmap[fld]['alias'], fld)
            d.exec_()
            # The user *must* give a value.  I'll take whatever is checked even if the
            # window was just closed!!
            derived = d.getValue()
        for fld in mlist:
            if not self.hasValue(True, idx, fld):
                self.createval(None, idx, fld)    # Everyone needs to have a value!
            if fld == derived:
                # The derived value must be None!
                if cfg[fld] == None:
                    try:
                        del self.edits[idx][fld]
                        if self.edits[idx] == {}:
                            del self.edits[idx]
                    except:
                        pass
                else:
                    try:
                        self.edits[idx][fld] = None
                    except:
                        self.edits[idx] = {fld: None}
        cm = chr(param.params.pobj.fldmap[derived]['colorder']+0x40)
        if cm in curmutex:
            curmutex = curmutex[:setidx] + ' ' + curmutex[setidx+1:]
            curmutex = self.promote(idx, derived, curmutex.index(cm), curmutex)
        curmutex = curmutex[:setidx] + cm + curmutex[setidx+1:]
        try:
            e = self.edits[idx]['mutex']
        except:
            e = cfg['mutex']
        e = e[:setidx] + cm + e[setidx+1:]
        try:
            self.edits[idx]['mutex'] = e
        except:
            self.edits[idx] = {'mutex': e}
        for fld in mlist:
            if fld != f:
                cnew = param.params.pobj.fldmap[fld]['cfgidx'] + self.coff
                self.fixChildren(idx, fld, cnew, self.getval(idx, fld), param.params.blue, setidx, cm)
        return curmutex

    def fixChildren(self, idx, f, column, v, chcolor, setidx=None, cm=None):
        for c in self.tree[idx]['children']:
            cd = self.getCfg(c)
            if not cd['_color'][f] in [param.params.blue, param.params.purple, param.params.almond]:
                continue
            if v == None:
                cd[f] = None
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
            if setidx != None:
                cd['curmutex'] = cd['curmutex'][:setidx] + cm + cd['curmutex'][setidx+1:]
            self.fixChildren(c, f, column, v, cd['_color'][f], setidx, cm)
        
    def setCurIdx(self, id):
        self.curidx = id
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        idx = id
        path = [idx];
        while self.tree[idx]['link'] != None:
            idx = self.tree[idx]['link']
            if idx == self.curidx:
                break
            path[:0] = [idx]
        for c in self.tree[id]['children']:
            if not c in path:
                path.append(c)
        self.path = path
        self.setRowCount(len(path))
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def selectConfig(self, cfg):
        param.params.ui.treeWidget.setCurrentItem(self.tree[cfg]['item'])
        
    def treeNavigation(self, cur, prev):
        if cur != None:
            self.setCurIdx(cur.id)

    def treeCollapse(self, item):
        if item != None:
            self.is_expanded[item.id] = False

    def treeExpand(self, item):
        if item != None:
            self.is_expanded[item.id] = True

    def hasValue(self, v, index, f=None):
        if f == None:
            if index.column() < self.coff:  # These values just aren't deleteable!
                return False
            (idx, f) = self.index2db(index)
        else:
            idx = index
        ev = self.geteditval(idx, f)
        if ev != None:
            return ev == v
        d = self.getCfg(idx)
        return d['_val'][f] == v

    def checkStatus(self, index, vals):
        (idx, f) = self.index2db(index)
        s = self.status[idx]
        for v in vals:
            if v in s:
                return True
        return False

    def ownTest(self, index):
        idx = self.path[index.row()]
        return idx < 0 or param.params.pobj.cfgs[idx]['owner'] == param.params.hutch
        
    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new child", self.createnew)
        menu.addAction("Clone existing", self.clone)
        menu.addAction("Clone values", self.clonevals)
        menu.addAction("Change parent", self.chparent,
                       lambda t, i: self.ownTest(i) and i.column() == self.cfgcol)
        menu.addAction("Delete value", self.deleteallval,
                       lambda t, i: self.ownTest(i) and self.hasValue(True, i))
        menu.addAction("Create value", self.createallval,
                       lambda t, i: self.ownTest(i) and self.hasValue(False, i))
        menu.addAction("Delete config", self.deletecfg,
                       lambda t, i: self.ownTest(i) and not self.checkStatus(i, 'D'))
        menu.addAction("Undelete config", self.undeletecfg,
                       lambda t, i: self.checkStatus(i, 'D'))
        menu.addAction("Commit this config", self.commitone,
                       lambda t, i: self.checkStatus(i, 'DMN'))
        menu.addAction("Revert this config", self.revertone,
                       lambda t, i: self.checkStatus(i, 'M'))
        table.addContextMenu(menu)
        colmgr.addColumnManagerMenu(table)

    def create_child(self, parent, sibling=None, useval=False):
        id = self.nextid;
        self.nextid -= 1
        now = datetime.datetime.now()
        d = {'name': "NewConfig%d" % id, 'config': parent,
             'cfgname': param.params.db.getCfgName(parent), 'id': id, 'owner': param.params.hutch,
             'security': None, 'dt_created': now, 'dt_updated': now}
        self.status[id] = "N"
        param.params.db.setCfgName(id, d['name'])
        if sibling == None:
            vals = self.getCfg(parent)
        else:
            vals = sibling
        color = {}
        haveval = {}
        for f in param.params.pobj.cfgflds:
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
            haveval[fld] = True
        d['_color'] = color
        d['_val'] = haveval
        try:
            d['curmutex'] = vals['curmutex']
        except:
            # Sigh.  No curmutex means this comes from the ObjModel, which means
            # even the mutex field has the 'wrong' values set.  So we need to look
            # up the values from our parent.
            d['curmutex'] = self.getCfg(vals['config'])['curmutex']
        if sibling == None:
            d['mutex'] = len(param.params.pobj.mutex_sets)*' '
        elif useval:
            try:
                d['mutex'] = vals['curmutex']
            except:
                d['mutex'] = d['curmutex']
        else:
            d['mutex'] = vals['mutex']
        # Make sure this respects the mutex!
        for c in d['curmutex']:
            v = ord(c) - 0x40
            if v > 0:
                d[param.params.pobj.objflds[v-1]['fld']] = None
        self.editval[id] = {}
        self.cfgs[id] = d
        self.buildtree()
        try:
            param.params.ui.treeWidget.setCurrentItem(self.tree[id]['item'])
        except:
            pass
        return id

    def createnew(self, table, index):
        (idx, f) = self.index2db(index)
        id = self.create_child(idx)

    def clone(self, table, index):
        (idx, f) = self.index2db(index)
        parent = self.getCfg(idx)['config']
        id = self.create_child(parent, self.getCfg(idx))

    def clonevals(self, table, index):
        (idx, f) = self.index2db(index)
        parent = self.getCfg(idx)['config']
        id = self.create_child(parent, self.getCfg(idx), True)

    def deleteallval(self, table, index):
        (idx, f) = self.index2db(index)
        self.deleteval(table, index)
        m = param.params.pobj.fldmap[f]['mutex']
        for mi in m:
            for fld in param.params.pobj.mutex_sets[mi]:
                if self.hasValue(True, idx, fld):
                    self.deleteval(None, idx, fld)    # Everyone needs to have a value!
        if not param.params.pobj.fldmap[f]['setmutex']:
            return
        for s in param.params.pobj.setflds:
            if f in s:
                for fld in s:
                    if self.hasValue(True, idx, fld):
                        self.deleteval(None, idx, fld)

    def deleteval(self, table, index, f=None):
        if f == None:
            (idx, f) = self.index2db(index)
        else:
            idx = index
            index = self.db2index(idx, f)
        d = self.getCfg(idx)
        pidx = d['config']
        if pidx == None:
            return                     # Can't delete a value from a root class!
        p = self.getCfg(pidx)
        if self.geteditval(idx, f) == None:
            self.seteditval(idx, f, False)
        else:
            self.seteditval(idx, f, None)
        try:
            e = self.edits[idx]
            del e[f]
            if e == {}:
                del self.edits[idx]
            else:
                self.edits[idx] = e
        except:
            pass
        if index != None:
            self.setModifiedStatus(index, idx, d)
        if idx < 0:
            d['_color'][f] = param.params.blue
        elif self.geteditval(idx, f) != None:
            d['_color'][f] = param.params.red
        else:
            pcolor = p['_color'][f]
            if pcolor == param.params.red or pcolor == param.params.purple:
                d['_color'][f] = param.params.purple
            else:
                d['_color'][f] = param.params.blue
        if d[f] != p[f]:
            if idx < 0:
                d[f] = p[f]
            else:
                try:
                    e = self.edits[idx]
                    e[f] = p[f]
                    self.edits[idx] = e
                except:
                    self.edits[idx] = {f: p[f]}
        if index != None:
            self.dataChanged.emit(index, index)

    def createallval(self, table, index):
        (idx, f) = self.index2db(index)
        self.createval(table, index)
        try:
            m = param.params.pobj.fldmap[f]['mutex']
        except:
            return   # Some fields (like name) don't actually have a fldmap entry.
                     # But these don't have mutex/setmutex fields either.
        for mi in m:
            for fld in param.params.pobj.mutex_sets[mi]:
                if not self.hasValue(True, idx, fld):
                    self.createval(None, idx, fld)
        if not param.params.pobj.fldmap[f]['setmutex']:
            return
        for s in param.params.pobj.setflds:
            if f in s:
                for fld in s:
                    if not self.hasValue(True, idx, fld):
                        self.createval(None, idx, fld)

    def createval(self, table, index, f=None):
        if f == None:
            (idx, f) = self.index2db(index)
        else:
            idx = index
            index = self.db2index(idx, f)
        d = self.getCfg(idx)
        if self.geteditval(idx, f) == None:
            self.seteditval(idx, f, True)
        else:
            self.seteditval(idx, f, None)
        if index != None:
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
        if index != None:
            self.dataChanged.emit(index, index)

    def hasChildren(self, idx, checked=[]):
        for c in self.tree[idx]['children']:
            if not 'D' in self.status[c]:
                return True
        # Sigh.  We might have a circular dependency.
        newchecked = list(checked)
        newchecked[:0] = self.tree[idx]['children']
        for c in self.tree[idx]['children']:
            if not c in checked:
                if self.hasChildren(c, newchecked):
                    return True
        return False

    def checkSetMutex(self, d, e):
        for s in param.params.pobj.setflds:
            f = param.params.pobj.fldmap[s[0]]
            if not f['setmutex'] or f['obj']:
                continue
            try:
                z = f['enum'][0]
            except:
                z = 0
            vlist = []
            for f in s:
                try:
                    v = e[f]
                except:
                    v = d[f]
                if v != None and not param.equal(v, z):
                    if v in vlist:
                        return [param.params.pobj.fldmap[f]['alias'] for f in s]
                    else:
                        vlist.append(v)
        return []

    #
    # Try to commit a change.  We assume we are in a transaction already.
    #
    # Returns True if done processing, False if we need to do something
    # else first.
    #
    # If mustdo is True, cause an error if we can't do it.
    #
    def commit(self, idx, mustdo):
        d = self.getCfg(idx)
        try:
            name = self.edits[idx]['name']
        except:
            name = d['name']
        if not utils.permission(d['owner'], d['security']):
            param.params.pobj.transaction_error("Not Authorized to Change %s!" % name)
            return True
        if name[0:10] == "NewConfig-":
            param.params.pobj.transaction_error("Object cannot be named %s!" % name)
            return True
        if 'D' in self.status[idx]:
            # We can process the delete only if *no one* is using this!
            # We only have to check the configuration, the configDelete
            # will check the objects.
            if mustdo:
                if self.tree[idx]['children'] != []:
                    param.params.pobj.transaction_error("Configuration to be deleted has children!")
                else:
                    param.params.pobj.configDelete(idx)
            else:
                if self.hasChildren(idx):
                    param.params.pobj.transaction_error("Configuration to be deleted has children!")
                else:
                    param.params.pobj.configDelete(idx)
            return True
        else:
            # When is it OK to commit this?  If:
            #    - All the parents already exist.
            #    - We don't make a circular loop.
            #    - Any setmutex sets are OK. (All inherited or all different.)
            #    - Every nullok field, is non-null.
            #    - Every unique field has a value (we'll let mysql actually deal with uniqueness!)
            try:
                e = self.edits[idx]
            except:
                e = {}
            s = self.checkSetMutex(d, e)
            if s != []:
                param.params.pobj.transaction_error("Config %s does not have unique values for %s!" %
                                                  (name, str(s)))
                return True
            for f in param.params.pobj.cfgflds:
                if not f['nullok'] and d[f['fld']] == "":
                    param.params.pobj.transaction_error("Field %s cannot be NULL!" % f['fld'])
                    return True
                if f['unique'] and not d['_val'][f['fld']]:
                    param.params.pobj.transaction_error("Field %s must be unique and cannot be inherited!" % f['fld'])
                    return True
            try:
                p = self.edits[idx]['config']
            except:
                p = d['config']
            while p != None:
                if not param.params.db.cfgIsValid(p):
                    if mustdo:
                        param.params.pobj.transaction_error("Config %s has new uncommitted ancestors!" %
                                                          param.params.db.getCfgName(idx))
                        return True
                    else:
                        return False
                # If we are only committing one, we need to check the actual parents,
                # otherwise, we check the edited parents!
                if mustdo:
                    p = self.getCfg(p)['config']
                else:
                    try:
                        p = self.edits[p]['config']
                    except:
                        p = self.getCfg(p)['config']
                if p == idx:
                    return param.params.pobj.transaction_error("Config change for %s creates a dependency loop!" %
                                                             param.params.db.getCfgName(idx))
                    return True
            if 'N' in self.status[idx]:
                newid = param.params.pobj.configInsert(param.params.db.doMap(d))
                if newid != None:
                    param.params.db.addCfgmap(idx, newid)
            else:
                ee = {}
                for fld in ['name', 'config', 'mutex']:
                    try:
                        ee[fld] = e[fld]
                    except:
                        pass
                for f in param.params.pobj.cfgflds:
                    fld = f['fld']
                    try:
                        ee[fld] = e[fld]           # We have a new value!
                    except:
                        try:
                            if not self.editval[idx][fld]:  # We want to inherit now!
                                ee[fld] = None
                            else:                  # The new value is what we are already inheriting!
                                ee[fld] = d[fld]
                        except:
                            pass                   # No change!
                param.params.pobj.configChange(idx, param.params.db.doMap(ee))
            return True

    # Commit all of the changes.  Again, we assume we're in a transaction
    # already.
    def commitall(self, verify=True):
        todo = set([k for k in self.editval.keys() if self.editval[k] != {}])
        try:
            todo = todo.union(set(self.edits.keys()))
        except:
            pass
        # We only need to confirm the changes.  The new configs are always OK, and
        # we forbid the deletion of a used config!
        if verify and not self.confirmCommit(list(todo)):
            return
        todo = todo.union(set(self.cfgs.keys()))
        todo = todo.union(set([idx for idx in self.status.keys() if 'D' in self.status[idx]]))
        while todo != set([]):
            done = set([])
            for idx in todo:
                if self.commit(idx, False):
                    done = done.union(set([idx]))
            todo = todo.difference(done)
            if done == set([]):
                param.params.pobj.transaction_error("Configuration commit is not making progress!")
                return

    def commitone(self, table, index):
        (idx, f) = self.index2db(index)
        if not self.confirmCommit([idx]):
            return
        param.params.db.start_transaction()
        self.commit(idx, True)
        if param.params.db.end_transaction() and not param.params.debug:
            self.cfgChangeDone(idx)

    def revertall(self):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        for idx in self.edits.keys():
            self.revertone(None, idx, True)
        self.emit(QtCore.SIGNAL("layoutChanged()"))
        
    def revertone(self, table, index, doall=False):
        if doall:
            idx = index
        else:
            (idx, f) = self.index2db(index)
        try:
            newparent = self.edits[idx]['config']
        except:
            newparent = None
        try:
            del self.edits[idx]
        except:
            pass
        self.editval[idx] = {}
        c = self.getCfg(idx)
        del c['_color']
        c = self.getCfg(idx)
        self.status[idx] = self.status[idx].replace("M", "")
        self.revertchildren(idx, c['curmutex'], [], doall)
        if newparent != None:
            self.buildtree()
            self.setCurIdx(self.curidx)
        elif not doall:
            r = index.row()
            self.dataChanged.emit(self.index(r, 0), self.index(r, self.colcnt - 1))

    def revertchildren(self, idx, pmutex, lp, doall):
        for cidx in self.tree[idx]['children']:
            if cidx in lp:
                continue
            c = self.getCfg(cidx)
            v = self.getval(cidx, "mutex")
            mutex = ""
            for i in range(len(param.params.pobj.mutex_sets)):
                if v[i] != ' ':
                    mutex += v[i]
                else:
                    mutex += pmutex[i]
            for (k, v) in c['_val'].items():
                if k in self.cfld:
                    continue
                if v == False or chr(param.params.pobj.fldmap[k]['colorder']+0x40) in mutex:
                    c[k] = None
            del c['_color']
            c = self.getCfg(cidx)
        lp.append(idx)
        for cidx in self.tree[idx]['children']:
            self.revertchildren(cidx, self.getCfg(cidx)['curmutex'], lp, doall)
        
    def cfgChangeDone(self, idx=None):
        if idx != None:
            try:
                del self.edits[idx]
            except:
                pass
            try:
                del self.editval[idx]
            except:
                pass
            self.status[idx] = ""
            if idx < 0:
                del self.cfgs[idx]
        else:
            self.edits = {}
            self.editval = {}
            self.cfgs = {}
            for k in self.status.keys():
                if k < 0:
                    del self.status[k]
                else:
                    self.status[k] = ""
        self.buildtree()
        try:
            param.params.ui.treeWidget.setCurrentItem(self.tree[self.curidx]['item'])
        except:
            param.params.ui.treeWidget.setCurrentItem(self.tree[0]['item'])

    def deletecfg(self, table, index):
        (idx, f) = self.index2db(index)
        if idx >= 0:
            d = self.getCfg(idx)
            if d['config'] != None:
                self.status[idx] = "".join(sorted("D" + self.status[idx]))
                statidx = self.index(index.row(), self.statcol)
                self.dataChanged.emit(statidx, statidx)
            else:
                QtGui.QMessageBox.critical(None, "Error",
                                           "Cannot delete root configuration!",
                                           QtGui.QMessageBox.Ok)
        else:
            del self.cfgs[idx]
            del self.status[idx]
            self.buildtree()
            try:
                param.params.ui.treeWidget.setCurrentItem(self.tree[self.curidx]['item'])
            except:
                param.params.ui.treeWidget.setCurrentItem(self.tree[0]['item'])

    def undeletecfg(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.getCfg(idx)
        self.status[idx] = self.status[idx].replace("D", "")
        statidx = self.index(index.row(), self.statcol)
        self.dataChanged.emit(statidx, statidx)

    def chparent(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.getCfg(idx)
        if d['config'] == None:
            QtGui.QMessageBox.critical(None, "Error",
                                       "Cannot change parent of root class!",
                                       QtGui.QMessageBox.Ok)
            return
        if (param.params.cfgdialog.exec_("Select new parent for %s" % d['name'], d['config']) ==
            QtGui.QDialog.Accepted):
            (idx, f) = self.index2db(index)
            p = param.params.cfgdialog.result
            if p == d['id']:
                QtGui.QMessageBox.critical(None, "Error",
                                           "Cannot change parent to self!",
                                           QtGui.QMessageBox.Ok)
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
            idx = self.path[row]
            try:
                if (col != self.cfgcol and col != self.statcol and col != self.owncol and
                    (idx < 0 or param.params.pobj.cfgs[idx]['owner'] == param.params.hutch)):
                    flags = flags | QtCore.Qt.ItemIsEditable
            except:
                pass # We seem to get here too fast sometimes after a delete, so just forget it.
        return flags

    #
    # Return the set of changed configurations.
    #
    # idx is the config we are currently looking at.
    # e is a list of values that have edits in this configuration.
    # s is the set of previously examined configurations.
    # l is the list of things we want to consider changed.  (That is
    # the configurations in l should have their edited values considered,
    # and the ones *not* in l should have their *original* values
    # considered.)
    #
    def findChange(self, idx, e, s, l):
        if idx in s:
            return s
        s.add(idx)
        for c in self.tree[idx]['children']:
            # OK, idx has changed fields in e and we want to check if this affects c.
            # However, c might be changed as well!
            #
            # Therefore, we pass in the list l of things that are concurrently changing
            # right now so we know where to look!
            if c in l:
                el = [f for f in e if not self.hasValue(True, c, f)]
            else:
                d = self.getCfg(c)
                el = [f for f in e if not d['_val'][f]]
            if el != []:
                s = self.findChange(c, el, s, l)
        return s

    def confirmCommit(self, l=None):
        if l == None:
            todo = set([k for k in self.editval.keys() if self.editval[k] != {}])
            try:
                todo = todo.union(set(self.edits.keys()))
            except:
                pass
            l = list(todo)
        chg = {}
        chgall = set([])
        for idx in l:
            try:
                e = self.edits[idx].keys()
                chg[idx] = self.findChange(idx, e, set([]), l)
            except:
                # No changed values --> no child changes!
                chg[idx] = set([idx])
            chgall = chgall.union(chg[idx])
        nc = len(chgall)
        no = param.params.pobj.countInstance(chgall)
        d = param.params.confirmdialog
        if nc == 0 and no == 0:
            return True
        d.ui.label.setText("This commit will affect %d configurations and %d motors." %
                           (nc, no))
        return d.exec_() == QtGui.QDialog.Accepted

    def editorInfo(self, index):
        c = index.column()
        if c < self.coff:
            return str
        try:
            return param.params.pobj.cfgflds[c - self.coff]['enum']
        except:
            return param.params.pobj.cfgflds[c - self.coff]['type']

    def cfgrenumber(self, old, new):
        for d in self.edits.values():
            try:
                if d['config'] == old:
                    d['config'] = new
            except:
                pass
        for d in self.cfgs.values():
            if d['config'] == old:
                d['config'] = new
        if old in self.tree.keys():
            self.tree[new] = self.tree[old]
            del self.tree[old]
        for d in self.tree.values():
            if d['link'] == old:
                d['link'] = new
            try:
                d['children'][d['children'].index(old)] = new
            except:
                pass
        try:
            self.root[index(self.root, old)] = new
        except:
            pass
        if old == self.curidx:
            self.setCurIdx(new)
