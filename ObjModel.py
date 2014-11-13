from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr
import datetime
import utils
import pyca

class ObjModel(QtGui.QStandardItemModel):
    cname   = ["Status", "Name", "Config", "PV Base"]
    cfld    = ["status", "name", "cfgname", "rec_base"]
    coff    = len(cname)
    statcol = 0
    namecol = 1
    cfgcol  = 2
    pvcol   = 3
    mutable = 2  # The first non-frozen column
    
    def __init__(self, db, ui, model):
        QtGui.QStandardItemModel.__init__(self)
        self.db = db
        self.ui = ui
        self.model = model
        self.pvdict = {}
        self.edits = {}
        self.objs = {}
        self.nextid = -1
        self.lastsort = (0, QtCore.Qt.DescendingOrder)
        # Setup headers
        self.colcnt = self.db.objfldcnt + self.coff
        self.setColumnCount(self.colcnt)
        self.setRowCount(len(self.db.objs))
        self.rowmap = self.db.objs.keys()
        font = QtGui.QFont()
        font.setBold(True)
        for c in range(self.colcnt):
            if c < self.coff:
                self.setHorizontalHeaderItem(c, QtGui.QStandardItem(self.cname[c]))
            else:
                self.setHorizontalHeaderItem(c, QtGui.QStandardItem(self.db.objflds[c-self.coff]['alias']))
        self.setHeaderData(self.statcol, QtCore.Qt.Horizontal,
                           QtCore.QVariant("C = All PVs Connected\nD = Deleted\nM = Modified\nN = New"),
                           QtCore.Qt.ToolTipRole)
        self.connectAllPVs()

    def index2db(self, index):
        c = index.column()
        if c < self.coff:
            return (self.rowmap[index.row()], self.cfld[c])
        else:
            return (self.rowmap[index.row()], self.db.objflds[c-self.coff]['fld'])

    def getObj(self, idx):
        if idx >= 0:
            return self.db.objs[idx]
        else:
            return self.objs[idx]

    def getCfg(self, idx, f):
        try:
            return self.edits[idx][f]
        except:
            pass
        if f in self.cfld or self.db.fldmap[f]['obj']:
            return self.getObj(idx)[f]
        else:
            try:
                cfg = self.edits[idx]['config']
            except:
                cfg = self.getObj(idx)['config']
            try:
                return self.model.edits[cfg][f]
            except:
                return self.model.getCfg(cfg)[f]
        
    def data(self, index, role = QtCore.Qt.DisplayRole):
        if (role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole and
            role != QtCore.Qt.ForegroundRole and role != QtCore.Qt.BackgroundRole):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return QtCore.QVariant()
        try:
            (idx, f) = self.index2db(index)
            d = self.getObj(idx)
            if role == QtCore.Qt.BackgroundRole:
                if d[f] == None:
                    return QtCore.QVariant(param.params.gray)
                else:
                    return QtCore.QVariant(param.params.white)
            try:
                v = self.edits[idx][f]
                if role == QtCore.Qt.ForegroundRole:
                    return QtCore.QVariant(param.params.red)
                else:
                    return QtCore.QVariant(v)
            except:
                v = d[f]                 # Actual value
                if role != QtCore.Qt.ForegroundRole or v == None:
                    return QtCore.QVariant(v)
                v2 = self.getCfg(idx, f) # Configured value
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
        # OK, the config/cfgname thing is slightly weird.  The field name for our index is
        # 'cfgname', but we are passing an int that should go to 'config'.  So we need to
        # change *both*!
        if f == 'cfgname':
            vlink = v
            v = self.db.getCfgName(vlink)
        try:
            del d[f]
            if f == 'cfgname':
                del d['config']
        except:
            pass
        v2 = self.getCfg(idx, f)
        if not param.equal(v, v2):
            d[f] = v
            if f == 'cfgname':
                d['config'] = vlink
            if not hadedit and idx >= 0:
                r = self.getObj(idx)
                r['status'] = "".join(sorted("M" + r['status']))
                self.statchange(idx)
        else:
            if hadedit and d == {} and idx >= 0:
                r = self.getObj(idx)
                r['status'] = r['status'].replace("M", "")
                self.statchange(idx)
        if d != {}:
            if idx < 0:
                self.objs[idx].update(d)
            else:
                self.edits[idx] = d
        else:
            try:
                del self.edits[idx]
            except:
                pass
        if f == 'rec_base':
            self.connectPVs(idx)
            r = index.row()
            self.dataChanged.emit(self.index(r, 0), self.index(r, self.colcnt))
        else:
            self.dataChanged.emit(index, index)
        return True
        
    def sortkey(self, idx, c):
        if c < self.coff:
            f = self.cfld[c]
        else:
            f = self.db.objflds[c-self.coff]['fld']
        try:
            return self.edits[idx][f]
        except:
            return self.getObj(idx)[f]

    def sort(self, Ncol, order):
        if (Ncol, order) != self.lastsort:
            self.lastsort = (Ncol, order)
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.rowmap = sorted(self.rowmap, key=lambda idx: self.sortkey(idx, Ncol))
            if order == QtCore.Qt.DescendingOrder:
                self.rowmap.reverse()
            self.emit(QtCore.SIGNAL("layoutChanged()"))

    def objchange(self):
        print "ObjModel has object change!"
        self.connectAllPVs()
        self.sort(self.lastsort[0], self.lastsort[1])

    def cfgchange(self):
        print "ObjModel has config change!"
        # This is really a sledgehammer.  Maybe we should check what really needs changing?
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def statchange(self, id):
        try:
            idx = self.index(self.rowmap.index(id), self.statcol)
            self.dataChanged.emit(idx, idx)
        except:
            pass

    def connectPVs(self, idx):
        pyca.attach_context()
        try:
            oldpvdict = self.pvdict[idx]
        except:
            oldpvdict = {}
        d = self.getObj(idx)
        try:
            base = self.edits[idx]['rec_base']
        except:
            base = d['rec_base']
        newpvdict = {}
        d['connstat'] = self.db.objfldcnt*[False]
        d['status'] = d['status'].replace("C", "")
        if base != "":
            for ofld in self.db.objflds:
                n = base + ofld['pv']
                f = ofld['fld']
                try:
                    pv = oldpvdict[n]
                    d[f] = pv.value
                    d['connstat'][ofld['objidx']] = True
                    del oldpvdict[n]
                except:
                    d[f] = None
                    pv = utils.monitorPv(n, self.pv_handler)
                    if ofld['type'] == str:
                        pv.set_string_enum(True)
                newpvdict[n] = pv
                pv.obj = d
                pv.fld = f
        if reduce(lambda a,b: a and b, d['connstat']):
            del d['connstat']
            d['status'] = "".join(sorted("C" + d['status']))
            self.statchange(idx)
        self.pvdict[idx] = newpvdict
        for pv in oldpvdict.values():
            pv.disconnect()

    def connectAllPVs(self):
        for idx in self.rowmap:
            self.connectPVs(idx)

    def pv_handler(self, pv, e):
        if e is None:
            pv.obj[pv.fld] = pv.value
            idx = self.db.fldmap[pv.fld]['objidx']
            try:
                pv.obj['connstat'][idx] = True
                if reduce(lambda a,b: a and b, pv.obj['connstat']):
                    del pv.obj['connstat']
                    pv.obj['status'] = "".join(sorted("C" + pv.obj['status']))
                    self.statchange(pv.obj['id'])
            except:
                pass
            try:
                index = self.index(self.rowmap.index(pv.obj['id']), idx + self.coff)
                self.dataChanged.emit(index, index)
            except:
                pass

    def haveNewName(self, idx, name):
        name = str(name)
        utils.fixName(self.db.objs.values(), idx, name)
        utils.fixName(self.objs.values(), idx, name)
        utils.fixName(self.edits.values(), idx, name)
        for i in range(len(self.rowmap)):
            idx = self.rowmap[i]
            try:
                if self.edits[idx]['config'] == idx:
                    self.edits[idx]['cfgname'] = str(name)
                    index = self.index(i, self.cfgcol)
                    self.dataChanged.emit(index, index)
            except:
                d = self.getObj(idx)
                if d['config'] == idx:
                    d['cfgname'] = str(name)
                    index = self.index(i, self.cfgcol)
                    self.dataChanged.emit(index, index)

    def checkStatus(self, index, vals):
        (idx, f) = self.index2db(index)
        s = self.getObj(idx)['status']
        for v in vals:
            if v in s:
                return True
        return False

    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new object", self.create)
        menu.addAction("Delete this object", self.delete,     lambda table, index: not self.checkStatus(index, 'D'))
        menu.addAction("Undelete this object", self.undelete, lambda table, index: self.checkStatus(index, 'D'))
        menu.addAction("Change configuration", self.chparent, lambda table, index: index.column() == self.cfgcol)
        menu.addAction("Commit this object", self.commitone,  lambda table, index: self.checkStatus(index, 'DMN'))
        menu.addAction("Apply to this object", self.applyone, lambda table, index: self.checkStatus(index, 'DMN'))
        table.addContextMenu(menu)

        colmgr.addColumnManagerMenu(table)

    def create(self, table, index):
        idx = self.nextid;
        self.nextid -= 1
        now = datetime.datetime.now()
        d = {'id': idx, 'config': 0, 'owner': self.db.hutch, 'name': "NewObject%d" % idx,
             'rec_base': "", 'dt_created': now, 'dt_updated': now, 'status': "N",
             'cfgname': self.db.getCfgName(0) }
        for o in self.db.objflds:
            if o['obj']:
                t = o['type']
                if t == str:
                    v = ""
                elif t == int:
                    v = 0
                else:
                    v = 0.0   # Must be float, since this is returned from db.m2pType.
                d[o['fld']] = v
            else:
                d[o['fld']] = None
        self.objs[idx] = d
        self.rowmap.append(idx)
        self.setRowCount(len(self.rowmap))
        lastsort = self.lastsort
        self.lastsort = (None, None)
        self.sort(lastsort[0], lastsort[1])

    def delete(self, table, index):
        (idx, f) = self.index2db(index)
        r = self.getObj(idx)
        r['status'] = "".join(sorted("D" + r['status']))
        self.statchange(idx)

    def undelete(self, table, index):
        (idx, f) = self.index2db(index)
        r = self.getObj(idx)
        r['status'] = r['status'].replace("D", "")
        self.statchange(idx)

    def commitone(self, table, index):
        (idx, f) = self.index2db(index)
        print "Commit Object %d" % idx
        return True

    def applyone(self, table, index):
        if self.commitone(table, index):
            (idx, f) = self.index2db(index)
            print "Apply Object %d" % idx

    def commitall(self):
        print "Commit All"
        return True

    def applyall(self):
        if self.commitall():
            print "Apply All"

    def chparent(self, table, index):
        (idx, f) = self.index2db(index)
        d = self.getObj(idx)
        if (param.params.cfgdialog.exec_("Select new configuration for %s" % d['name'], d['config']) ==
            QtGui.QDialog.Accepted):
            self.setData(index, QtCore.QVariant(param.params.cfgdialog.result))
            r = index.row()
            self.dataChanged.emit(self.index(r, 0), self.index(r, self.colcnt - 1))

    def cfgEdit(self, idx, f):
        f = str(f)
        if f == 'cfgname':
            c1 = 0
            c2 = self.colcnt - 1
        else:
            try:
                c1 = self.coff + self.db.fldmap[f]['objidx']
                c2 = c1
            except:
                # We shouldn't be here.
                return
        for i in range(len(self.rowmap)):
            id = self.rowmap[i]
            try:
                cfg = self.edits[id]['config']
            except:
                cfg = self.getObj(id)['config']
            if cfg == idx:
                self.dataChanged.emit(self.index(i, c1), self.index(i, c2))

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
