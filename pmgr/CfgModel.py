import datetime
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from . import colmgr
from . import param
from . import utils


try:
    QString = unicode
except NameError:
    # Python 3
    QString = str

class CfgModel(QtGui.QStandardItemModel):
    """
    This is the Model (from the Model-View-Controller paradigm) supporting
    the configuration table.  This is a 2D table: rows are configurations,
    and columns are configuration values.

    The heart of this is two routines:
        data(index, role) takes a QModelIndex and a Qt.DisplayRole and returns
        the value corresponding to that location in the table.

        setData(index, value, role) takes a QModelIndex and a new value, and
        stores that value into the table for the specified role.
    """
    newname = QtCore.pyqtSignal(int, 'QString')
    cfgChanged = QtCore.pyqtSignal(int, 'QString')
    
    layoutAboutToBeChanged = QtCore.pyqtSignal()
    layoutChanged = QtCore.pyqtSignal()
    cname   = ["Status", "Name", "Parent"]
    cfld    = ["status", "name", "cfgname"]
    ctips   = ["D = Deleted\nM = Modified\nN = New", "Configuration Name", "Parent Configuration"]
    coff    = len(cname)
    statcol = 0
    namecol = 1
    cfgcol  = 2
    mutable = 2   # The first non-frozen column
    fixflds = ["status", "cfgname"]
    
    def __init__(self):
        QtGui.QStandardItemModel.__init__(self)
        self.curidx = 0
        self.path = []
        self.edits = {}
        self.cfgs = {}
        self.status = {}
        self.nextid = -1
        param.params.ui.treeWidget.currentItemChanged.connect(self.treeNavigation)
        param.params.ui.treeWidget.itemCollapsed.connect(self.treeCollapse)
        param.params.ui.treeWidget.itemExpanded.connect(self.treeExpand)
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
        self.hutchid = -1
        self.buildtree()
        param.params.ui.treeWidget.expandItem(self.tree[0]['item']) # Expand DEFAULT.
        try:
            param.params.ui.treeWidget.setCurrentItem(self.tree[self.hutchid]['item'])
            self.curidx = self.hutchid
        except:
            self.setCurIdx(0)
        if self.curidx != 0:
            param.params.ui.treeWidget.expandItem(self.tree[self.curidx]['item'])
        s = ""
        for f in param.params.pobj.mutex_flds:
            s += chr(param.params.pobj.fldmap[f]['colorder']+0x40)
        self.mutex_flds = s

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
        hutch = param.params.pobj.hutch.upper()
        for id in r:
            if id in d:
                continue
            d.append(id)
            if id in self.root:
                item = QtWidgets.QTreeWidgetItem(tree)
                parent = None
            else:
                item = QtWidgets.QTreeWidgetItem()
                parent = t[id]['link']
            item.id = id
            item.setText(0, t[id]['name'])
            if t[id]['name'] == hutch:
                self.hutchid = id
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

    def getCfg(self, idx):
        """
        Get the configuration dictionary for this index.

        Negative indices have not been committed yet and are locally 
        stored in self.cfgs.  Positive indices are in the database and
        are kept in the pmgrobj.

        This routine also creates a "_color" dictionary that gives the
        modification status of each field.
        """
        if idx == None:
            return {}
        if idx >= 0:
            d = param.params.pobj.cfgs[idx]
        else:
            d = self.cfgs[idx]
        try:
            e = self.edits[idx].keys()
        except:
            e = []
        if not '_color' in d.keys():
            color = {}
            try:
                v = self.edits[idx]['mutex']
            except:
                v = d['mutex']
            d['curmutex'] = v
            for (k, v) in d.items():
                if k[:3] != 'PV_' and k[:4] != 'FLD_' and not k in self.cfld:
                    continue
                if v == None and chr(param.params.pobj.fldmap[k]['colorder']+0x40) in d['curmutex']:
                    color[k] = param.params.almond
                elif k in e:
                    color[k] = param.params.red
                else:
                    color[k] = param.params.black
            d['_color'] = color
        return d

    def getval(self, idx, f):
        try:
            return self.edits[idx][f]
        except:
            return self.getCfg(idx)[f]

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if (role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole and
            role != QtCore.Qt.ForegroundRole and role != QtCore.Qt.BackgroundRole and
            role != QtCore.Qt.ToolTipRole):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return None
        (idx, f) = self.index2db(index)
        if role == QtCore.Qt.ToolTipRole:
            # We'll make this smarter later!
            return QtGui.QStandardItemModel.data(self, index, role)
        if f == "status":
            if role == QtCore.Qt.BackgroundRole:
                return param.params.white
            elif role == QtCore.Qt.ForegroundRole:
                return param.params.black
            else:
                return self.status[idx]
        d = self.getCfg(idx)
        if role == QtCore.Qt.ForegroundRole:
            color = d['_color'][f]
            return color
        elif role == QtCore.Qt.BackgroundRole:
            if f in self.cfld:
                return param.params.white
            if chr(param.params.pobj.fldmap[f]['colorder']+0x40) in d['curmutex']:
                return param.params.almond
            else:
                return param.params.white
        else:
            try:
                v = self.edits[idx][f]
            except:
                v = d[f]
            return v
        
    def setData(self, index, v, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole:
            return QtGui.QStandardItemModel.setData(self, index, value, role)
        (idx, f) = self.index2db(index)
        # Get all the edits for this config.
        try:
            e = self.edits[idx]
        except:
            e = {}
        # OK, the config/cfgname thing is slightly weird.  The field name for our index is
        # 'cfgname', but we are passing an int that should go to 'config'.  So we need to
        # change *both*!  More than that, it's possible that the configuration name has been
        # edited!
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
        else:
            d['_color'][f] = param.params.black
        c = index.column()
        try:
            cm = chr(param.params.pobj.fldmap[f]['colorder']+0x40)
            if cm in d['curmutex']:
                # This was a calculated value!
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
        return curmutex
        
    def setCurIdx(self, id):
        self.curidx = id
        self.layoutAboutToBeChanged.emit()
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
        self.layoutChanged.emit()

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

    def checkStatus(self, index, vals):
        (idx, f) = self.index2db(index)
        s = self.status[idx]
        for v in vals:
            if v in s:
                return True
        return False

    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new child", self.createnew)
        menu.addAction("Clone existing", self.clone)
        menu.addAction("Change parent", self.chparent,
                       lambda t, i: i.column() == self.cfgcol)
        menu.addAction("Delete config", self.deletecfg,
                       lambda t, i: not self.checkStatus(i, 'D'))
        menu.addAction("Undelete config", self.undeletecfg,
                       lambda t, i: self.checkStatus(i, 'D'))
        menu.addAction("Commit this config", self.commitone,
                       lambda t, i: self.checkStatus(i, 'DMN'))
        menu.addAction("Revert this config", self.revertone,
                       lambda t, i: self.checkStatus(i, 'M'))
        table.addContextMenu(menu)
        colmgr.addColumnManagerMenu(table)

    #
    # How is this called?
    #     - Parent is the parent configuration idx.
    #     - Sibling is the sibling configuration dictionary.
    #     - diff is True if we are actually using an object dictionary.
    # So three ways to use this:
    #     - Create configuration from object
    #     - Create new child
    #     - Clone existing
    #
    def create_child(self, parent, sibling, diff=False):
        id = self.nextid;
        self.nextid -= 1
        now = datetime.datetime.now()
        d = {'name': "NewConfig%d" % id, 'config': parent,
             'cfgname': param.params.db.getCfgName(parent), 'id': id, 
             'dt_created': now, 'dt_updated': now}
        self.status[id] = "N"
        param.params.db.setCfgName(id, d['name'])
        color = {}
        for f in param.params.pobj.cfgflds:
            fld = f['fld']
            d[fld] = sibling[fld]
            color[fld] = param.params.black
        for fld in self.cfld:
            color[fld] = param.params.black
        d['_color'] = color
        if diff:
            # Sigh.  The sibling is from the object model, which means that the
            # the mutex field has the 'wrong' values set.  What we *really* want
            # is the mutex field of the object's config!
            d['curmutex'] = self.getCfg(sibling['config'])['curmutex']
            d['mutex'] = d['curmutex']
        else:
            d['curmutex'] = sibling['curmutex']
            d['mutex'] = sibling['mutex']
        # Make sure this respects the mutex! MCB
        for c in d['curmutex']:
            v = ord(c) - 0x40
            if v > 0:
                d[param.params.pobj.objflds[v-1]['fld']] = None
        self.cfgs[id] = d
        self.buildtree()
        try:
            param.params.ui.treeWidget.setCurrentItem(self.tree[id]['item'])
        except:
            pass
        return id

    def createnew(self, table, index):
        (idx, f) = self.index2db(index)
        id = self.create_child(idx, self.getCfg(idx))

    def clone(self, table, index):
        (idx, f) = self.index2db(index)
        parent = self.getCfg(idx)['config']
        id = self.create_child(parent, self.getCfg(idx))

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
        if not utils.permission():
            param.params.pobj.transaction_error("Not Authorized to Change %s!" % name)
            return True
        if name[0:10] == "NewConfig-":
            param.params.pobj.transaction_error("Object cannot be named %s!" % name)
            return True
        if 'D' in self.status[idx]:
            # We can process the delete only if *no one* is using this!
            if mustdo:
                if self.tree[idx]['children'] != []:
                    param.params.pobj.transaction_error("Configuration to be deleted has children!")
                elif param.params.objmodel.configInUse(idx):
                    param.params.pobj.transaction_error("Object still using configuration to be deleted!")
                else:
                    param.params.pobj.configDelete(idx)
            else:
                if self.hasChildren(idx):
                    param.params.pobj.transaction_error("Configuration to be deleted has children!")
                elif param.params.objmodel.configInUse(idx):
                    param.params.pobj.transaction_error("Object still using configuration to be deleted!")
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
        try:
            todo = todo.union(set(self.edits.keys()))
        except:
            todo = set([])
        # We only need to confirm the changes.  We forbid the deletion of a used config!
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
        self.layoutAboutToBeChanged.emit()
        for idx in self.edits.keys():
            self.revertone(None, idx, True)
        self.layoutChanged.emit()
        
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
        c = self.getCfg(idx)
        del c['_color']
        c = self.getCfg(idx)
        self.status[idx] = self.status[idx].replace("M", "")
        if newparent != None:
            self.buildtree()
            self.setCurIdx(self.curidx)
        elif not doall:
            r = index.row()
            self.dataChanged.emit(self.index(r, 0), self.index(r, self.colcnt - 1))
        
    def cfgChangeDone(self, idx=None):
        if idx != None:
            try:
                del self.edits[idx]
            except:
                pass
            self.status[idx] = ""
            if idx < 0:
                del self.cfgs[idx]
        else:
            self.edits = {}
            self.cfgs = {}
            snew = {}
            for k in self.status.keys():
                if k >= 0:
                    snew[k] = ""
            self.status = snew
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
                QtWidgets.QMessageBox.critical(None, "Error",
                                           "Cannot delete root configuration!",
                                           QtWidgets.QMessageBox.Ok)
        elif param.params.objmodel.configInUse(idx):
            QtWidgets.QMessageBox.critical(None, "Error",
                                           "Cannot delete configuration still in use!",
                                           QtWidgets.QMessageBox.Ok)
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
            QtWidgets.QMessageBox.critical(None, "Error",
                                       "Cannot change parent of root class!",
                                       QtWidgets.QMessageBox.Ok)
            return
        if (param.params.cfgdialog.exec_("Select new parent for %s" % d['name'], d['config']) ==
            QtWidgets.QDialog.Accepted):
            (idx, f) = self.index2db(index)
            p = param.params.cfgdialog.result
            if p == d['id']:
                QtWidgets.QMessageBox.critical(None, "Error",
                                           "Cannot change parent to self!",
                                           QtWidgets.QMessageBox.Ok)
                return
            self.setData(index, param.params.cfgdialog.result)
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
                if (col != self.cfgcol and col != self.statcol):
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
        return s

    def confirmCommit(self, l=None):
        if l == None:
            try:
                todo = todo.union(set(self.edits.keys()))
            except:
                todo = ([])
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
        return d.exec_() == QtWidgets.QDialog.Accepted

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

    def modifycfgfromobj(self, obj):
        idx = obj['config']
        cfg = self.getCfg(idx)
        if obj['config'] not in self.path:
            self.setCurIdx(idx)
        r = self.path.index(idx)
        for c in range(self.coff, self.colcnt):
            f = param.params.pobj.cfgflds[c-self.coff]['fld']
            o = param.params.pobj.cfgflds[c-self.coff]['colorder']
            cc = chr(o+0x40)
            if cc in self.mutex_flds and cc not in cfg['curmutex']:
                continue
            try:
                if obj[f] != cfg[f]:
                    self.setData(self.index(r, c), obj[f])
            except:
                pass
