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
    ctips   = ["C = All PVs Connected\nD = Deleted\nM = Modified\nN = New\nX = Inconsistent",
               "Object Name", "Configuration Name", "PV Base Name"]
    coff    = len(cname)
    statcol = 0
    namecol = 1
    cfgcol  = 2
    pvcol   = 3
    mutable = 2  # The first non-frozen column
    defflds = ["status", "name", "config", "cfgname", "rec_base", "FLD_DESC", "FLD_PORT"]
    fixflds = ["status"]
    
    def __init__(self):
        QtGui.QStandardItemModel.__init__(self)
        self.pvdict = {}
        self.edits = {}
        self.objs = {}
        self.status = {}
        self.istatus = {}
        self.nextid = -1
        self.lastsort = (0, QtCore.Qt.DescendingOrder)
        # Setup headers
        self.colcnt = param.params.db.objfldcnt + self.coff
        self.setColumnCount(self.colcnt)
        self.setRowCount(len(param.params.db.objs))
        self.rowmap = param.params.db.objs.keys()
        font = QtGui.QFont()
        font.setBold(True)
        for c in range(self.colcnt):
            if c < self.coff:
                i = QtGui.QStandardItem(self.cname[c])
                i.setToolTip(self.ctips[c])
            else:
                i = QtGui.QStandardItem(param.params.db.objflds[c-self.coff]['alias'])
                desc = param.params.db.objflds[c-self.coff]['tooltip']
                if desc != "":
                    i.setToolTip(desc)
            self.setHorizontalHeaderItem(c, i)
        self.createStatus()
        self.connectAllPVs()

    def createStatus(self):
        for d in param.params.db.objs.values():
            try:
                v = self.status[d['id']]
            except:
                self.status[d['id']] = ""
            try:
                v = self.istatus[d['id']]
            except:
                self.istatus[d['id']] = set([])

    def getStatus(self, idx):
        v = self.status[idx]
        if self.istatus[idx] != set([]):
            return "".join(sorted("X" + v))
        else:
            return v

    def index2db(self, index):
        c = index.column()
        if c < self.coff:
            return (self.rowmap[index.row()], self.cfld[c])
        else:
            return (self.rowmap[index.row()], param.params.db.objflds[c-self.coff]['fld'])

    def getObj(self, idx):
        if idx >= 0:
            return param.params.db.objs[idx]
        else:
            return self.objs[idx]

    def getCfg(self, idx, f, GetEdit=True):
        if GetEdit:
            try:
                return self.edits[idx][f]
            except:
                pass
        if f in self.cfld or f == 'mutex':
            return self.getObj(idx)[f]
        elif param.params.db.fldmap[f]['obj']:
            return self.getObj(idx)['_val'][f]
        else:
            try:
                cfg = self.edits[idx]['config']
            except:
                cfg = self.getObj(idx)['config']
            try:
                return param.params.cfgmodel.edits[cfg][f]
            except:
                return param.params.cfgmodel.getCfg(cfg)[f]
        
    def data(self, index, role = QtCore.Qt.DisplayRole):
        if (role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole and
            role != QtCore.Qt.ForegroundRole and role != QtCore.Qt.BackgroundRole and
            role != QtCore.Qt.ToolTipRole):
            return QtGui.QStandardItemModel.data(self, index, role)
        if not index.isValid():
            return QtCore.QVariant()
        (idx, f) = self.index2db(index)
        if role == QtCore.Qt.ToolTipRole:
            if f == 'status':
                return QtGui.QStandardItemModel.data(self, index, role)
            try:
                ve = self.edits[idx][f]     # Edited value
                if ve == None:
                    ve = "None"
            except:
                ve = None
            try:
                va = self.getObj(idx)[f]    # Actual value
            except:
                va = None
            vc = self.getCfg(idx, f, False) # Configured value
            if ve == None and (vc == None or param.equal(va, vc)):
                return QtGui.QStandardItemModel.data(self, index, role)
            v = "Configured Value: %s" % str(vc)
            v += "\nActual Value: %s" % str(va)
            if ve != None:
                v += "\nEdited Value: %s" % str(ve)
            return QtCore.QVariant(v)
        if f == "status":
            if role == QtCore.Qt.ForegroundRole:
                return QtCore.QVariant(param.params.black)
            elif role == QtCore.Qt.BackgroundRole:
                return QtCore.QVariant(param.params.white)
            else:
                return QtCore.QVariant(self.getStatus(idx))
        try:
            v = self.getObj(idx)[f]  # Actual value
        except:
            v = None
        v2 = self.getCfg(idx, f) # Configured value
        if v == None or v2 == None or param.equal(v, v2):
            try:
                self.istatus[idx].remove(f)     # If we don't have a value (either the PV isn't connected, or
                                                # it is a derived value in the configuration), or the PV is
                                                # equal to the configuration, we're not inconsistent.
            except:
                pass
        else:
            self.istatus[idx].add(f)          # Otherwise, we are!
        if role == QtCore.Qt.BackgroundRole:
            # If the actual value is None, the PV is not connected.
            # If the configuration value is None, the PV is derived.
            if f in self.cfld or param.params.db.fldmap[f]['obj']:
                # An object value!  Let "derived" win!
                if v2 == None:
                    return QtCore.QVariant(param.params.almond)    # A derived value.
                elif v == None:
                    return QtCore.QVariant(param.params.gray)      # Not connected.
                elif v == "" and v2 != "":
                    return QtCore.QVariant(param.params.ltblue)    # Actually empty, but there is a configured value.
                else:
                    return QtCore.QVariant(param.params.white)    # An ordinary cell.
            else:
                # A configuration value!  Let "not connected" win!
                if v == None:
                    return QtCore.QVariant(param.params.gray)      # Not connected.
                elif v == "" and v2 != "":
                    return QtCore.QVariant(param.params.ltblue)    # Actually empty, but there is a configured value.
                elif v2 == None:
                    return QtCore.QVariant(param.params.almond)    # A derived value.
                else:
                    return QtCore.QVariant(param.params.ltgray)     # An ordinary cell.
        elif role == QtCore.Qt.ForegroundRole:
            try:
                v = self.edits[idx][f]
                return QtCore.QVariant(param.params.red)
            except:
                pass
            if v2 == None or param.equal(v, v2):
                return QtCore.QVariant(param.params.black)
            else:
                return QtCore.QVariant(param.params.blue)
            return QtCore.QVariant()
        elif role == QtCore.Qt.DisplayRole:
            try:
                v = self.edits[idx][f]
                return QtCore.QVariant(v)
            except:
                pass
            return QtCore.QVariant(v)
        else:   # QtCore.Qt.EditRole
            try:
                v = self.edits[idx][f]
                return QtCore.QVariant(v)
            except:
                pass
            if v2 != None:
                return QtCore.QVariant(v2)
            else:
                return QtCore.QVariant(v)

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
            v = param.params.db.getCfgName(vlink)
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
                self.status[idx] = "".join(sorted("M" + self.status[idx]))
                self.statchange(idx)
        else:
            if hadedit and d == {} and idx >= 0:
                self.status[idx] = self.status[idx].replace("M", "")
                self.statchange(idx)
        if d != {}:
            if idx < 0:
                self.objs[idx].update(d)
                self.objs[idx]['_val'].update(d)
            else:
                self.edits[idx] = d
        else:
            try:
                del self.edits[idx]
                self.status[idx] = self.status[idx].replace("M", "")
                self.statchange(idx)
            except:
                pass
        mutex = self.getCfg(idx, 'mutex')
        try:
            cm = chr(param.params.db.fldmap[f]['colorder']+0x40)
            if cm in mutex:
                i = mutex.find(cm)
                self.promote(idx, f, i, mutex)
        except:
            pass
        if f == 'rec_base':
            self.connectPVs(idx)
            r = index.row()
            self.dataChanged.emit(self.index(r, 0), self.index(r, self.colcnt))
        else:
            self.dataChanged.emit(index, index)
        return True

    def promote(self, idx, f, setidx, curmutex):
        mlist = param.params.db.mutex_sets[setidx]
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
                    d.addValue(param.params.db.fldmap[fld]['alias'], fld)
            d.exec_()
            # The user *must* give a value.  I'll take whatever is checked even if the
            # window was just closed!!
            derived = d.getValue()
        for fld in mlist:
            if fld == derived:
                # The derived value must be None!
                if self.getObj(idx)['_val'][fld] == None:
                    try:
                        del self.edits[idx][fld]
                        if self.edits[idx] == {}:
                            del self.edits[idx]
                            self.status[idx] = self.status[idx].replace("M", "")
                            self.statchange(idx)
                    except:
                        pass
                else:
                    try:
                        self.edits[idx][fld] = None
                    except:
                        self.edits[idx] = {fld: None}
        cm = chr(param.params.db.fldmap[derived]['colorder']+0x40)
        if cm in curmutex:
            curmutex = curmutex[:setidx] + ' ' + curmutex[setidx+1:]
            curmutex = self.promote(idx, derived, curmutex.index(cm), curmutex)
        curmutex = curmutex[:setidx] + cm + curmutex[setidx+1:]
        if self.getObj(idx)['mutex'] == curmutex:
            try:
                del self.edits[idx]['mutex']
                if self.edits[idx] == {}:
                    del self.edits[idx]
                    self.status[idx] = self.status[idx].replace("M", "")
                    self.statchange(idx)
            except:
                pass
        else:
            try:
                self.edits[idx]['mutex'] = curmutex
            except:
                self.edits[idx] = {'mutex': curmutex}
        return curmutex
        
    def sortkey(self, idx, c):
        if c == self.statcol:
            return self.getStatus(idx)
        if c < self.coff:
            f = self.cfld[c]
        else:
            f = param.params.db.objflds[c-self.coff]['fld']
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
        self.createStatus()
        self.connectAllPVs()
        self.sort(self.lastsort[0], self.lastsort[1])

    def cfgchange(self):
        # This is really a sledgehammer.  Maybe we should check what really needs changing?
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def statchange(self, id):
        try:
            idx = self.index(self.rowmap.index(id), self.statcol)
            self.dataChanged.emit(idx, idx)
        except:
            pass

    #
    # Connect all of the PVs, and build a pv dictionary.  The dictionary
    # has two mappings: field to PV and pv name to PV.  We use the second
    # to find PVs we are already connected to, and we use the first to
    # find the PV when we apply.
    #
    def connectPVs(self, idx):
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
        d['connstat'] = param.params.db.objfldcnt*[False]
        self.status[idx] = self.status[idx].replace("C", "")
        if base != "":
            for ofld in param.params.db.objflds:
                n = base + ofld['pv']
                f = ofld['fld']
                try:
                    del oldpvdict[f]   # Get rid of the field mapping
                                       # so we don't disconnect the PV below!
                except:
                    pass
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
                newpvdict[f] = pv
                pv.obj = d
                pv.fld = f
        if reduce(lambda a,b: a and b, d['connstat']):
            del d['connstat']
            self.status[idx] = "".join(sorted("C" + self.status[idx]))
            self.statchange(idx)
        self.pvdict[idx] = newpvdict
        for pv in oldpvdict.values():
            try:
                pv.disconnect()
            except:
                pass

    def connectAllPVs(self):
        for idx in self.rowmap:
            try:
                self.connectPVs(idx)
            except:
                pass

    def pv_handler(self, pv, e):
        if e is None:
            pv.obj[pv.fld] = pv.value
            idx = param.params.db.fldmap[pv.fld]['objidx']
            try:
                pv.obj['connstat'][idx] = True
                if reduce(lambda a,b: a and b, pv.obj['connstat']):
                    del pv.obj['connstat']
                    self.status[pv.obj['id']] = "".join(sorted("C" + self.status[pv.obj['id']]))
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
        utils.fixName(param.params.db.objs.values(), idx, name)
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
        s = self.getStatus(idx)
        for v in vals:
            if v in s:
                return True
        return False

    def haveObjPVDiff(self, index):
        (idx, f) = self.index2db(index)
        db = param.params.db
        try:
            v = self.edits[idx][f]
        except:
            try:
                v = db.objs[idx]['_val'][f]
            except:
                return False
        try:
            return db.fldmap[f]['obj'] and not param.equal(db.objs[idx][f], v)
        except:
            return False

    def setupContextMenus(self, table):
        menu = utils.MyContextMenu()
        menu.addAction("Create new object", self.create)
        menu.addAction("Delete this object", self.delete,
                       lambda table, index: index.row() >= 0 and self.rowmap[index.row()] != 0 and
                       not self.checkStatus(index, 'D'))
        menu.addAction("Undelete this object", self.undelete,
                       lambda table, index: index.row() >= 0 and self.rowmap[index.row()] != 0 and
                       self.checkStatus(index, 'D'))
        menu.addAction("Change configuration", self.chparent,
                       lambda table, index: self.rowmap[index.row()] != 0 and index.column() == self.cfgcol)
        menu.addAction("Set from PV", self.setFromPV,
                       lambda table, index: index.row() >= 0 and self.rowmap[index.row()] != 0 and
                       self.haveObjPVDiff(index))
        menu.addAction("Create configuration from object", self.createcfg,
                       lambda table, index: index.row() >= 0 and self.rowmap[index.row()] != 0)
        menu.addAction("Commit this object", self.commitone,
                       lambda table, index: index.row() >= 0 and self.rowmap[index.row()] != 0 and
                       self.checkStatus(index, 'DMN'))
        menu.addAction("Apply to this object", self.applyone,
                       lambda table, index: index.row() >= 0 and self.rowmap[index.row()] != 0 and
                       self.checkStatus(index, 'DMN'))
        menu.addAction("Revert this object", self.revertone,
                       lambda table, index: self.checkStatus(index, 'M'))
        table.addContextMenu(menu)
        colmgr.addColumnManagerMenu(table)

    def setFromPV(self, table, index):
        (idx, f) = self.index2db(index)
        self.setData(index, QtCore.QVariant(param.params.db.objs[idx][f]))

    def create(self, table, index):
        idx = self.nextid;
        self.nextid -= 1
        now = datetime.datetime.now()
        d = dict(param.params.db.objs[0])
        dd = {'id': idx, 'config': 0, 'owner': param.params.hutch, 'name': "NewObject%d" % idx,
              'rec_base': "", 'dt_created': now, 'dt_updated': now,
              'cfgname': param.params.db.getCfgName(0) }
        d.update(dd)
        self.status[idx] = "N"
        self.istatus[idx] = set([])
        d['_val'] = dict(d)
        self.objs[idx] = d
        self.rowmap.append(idx)
        self.adjustSize()

    def adjustSize(self):
        self.setRowCount(len(self.rowmap))
        lastsort = self.lastsort
        self.lastsort = (None, None)
        self.sort(lastsort[0], lastsort[1])

    def createcfg(self, table, index):
        (idx, f) = self.index2db(index)
        param.params.cfgmodel.create_child(0, self.getObj(idx), True)

    def delete(self, table, index):
        (idx, f) = self.index2db(index)
        if idx >= 0:
            self.status[idx] = "".join(sorted("D" + self.status[idx]))
            self.statchange(idx)
        else:
            del self.objs[idx]
            del self.status[idx]
            del self.istatus[idx]
            self.rowmap.remove(idx)
            self.adjustSize()

    def undelete(self, table, index):
        (idx, f) = self.index2db(index)
        self.status[idx] = self.status[idx].replace("D", "")
        self.statchange(idx)

    #
    # Try to commit a change.  We assume we are in a transaction already.
    #
    def commit(self, idx):
        d = self.getObj(idx)
        if not utils.permission(d['owner'], None):
            param.params.db.transaction_error("Not Authorized!")
        try:
            if self.edits[idx]['name'][0:10] == "NewObject-":
                param.params.db.transaction_error("Object cannot be named %s!" % self.edits[idx]['name'])
                return
        except:
            pass
        if d['name'][0:10] == "NewObject-":
            param.params.db.transaction_error("Object cannot be named %s!" % d['name'])
            return
        if 'D' in self.status[idx]:
            param.params.db.objectDelete(idx)
        elif 'N' in self.status[idx]:
            param.params.db.objectInsert(self.getObj(idx))
        elif 'M' in self.status[idx]:
            param.params.db.objectChange(self.getObj(idx), self.edits[idx])

    def commitone(self, table, index):
        param.params.db.start_transaction()
        (idx, f) = self.index2db(index)
        self.commit(idx)
        if param.params.db.end_transaction():
            self.objChangeDone(idx)
            return True
        else:
            return False

    def commitall(self):
        param.params.db.start_transaction()
        for (idx, s) in self.status.items():
            if 'D' in s:
                self.commit(idx)
        param.params.cfgmodel.commitall()
        for (idx, s) in self.status.items():
            if ('N' in s or 'M' in s) and not 'D' in s:  # Paranoia.  We should never have DM or DN.
                self.commit(idx)
        if param.params.db.end_transaction():
            param.params.cfgmodel.cfgChangeDone()
            self.objChangeDone()
            return True
        else:
            return False

    def apply(self, idx):
        d = self.getObj(idx)
        pvd = self.pvdict[idx]
        for f in param.params.db.setflds:
            v = d[f]
            v2 = self.getCfg(idx, f) # Configured value
            if not param.equal(v, v2):
                try:
                    pv = pvd[f]
                    if param.params.debug:
                        print "Put %s to %s" % (str(v2), pv.name)
                    else:
                        pv.put(v2, -1.0)
                except:
                    pass

    def applyone(self, table, index):
        if self.commitone(table, index):
            (idx, f) = self.index2db(index)
            self.apply(idx)
            pyca.flush_io()

    def applyall(self):
        if self.commitall():
            for idx in self.rowmap:
                self.apply(idx)
            pyca.flush_io()

    def revertone(self, table, index):
        (idx, f) = self.index2db(index)
        try:
            del self.edits[idx]
        except:
            pass
        self.status[idx] = self.status[idx].replace("M", "")
        self.statchange(idx)

    def objChangeDone(self, idx=None):
        if idx != None:
            try:
                del self.edits[idx]
            except:
                pass
            if idx < 0:
                del self.objs[idx]
                del self.status[idx]
                del self.istatus[idx]
            else:
                if 'C' in self.status[idx]:
                    self.status[idx] = "C"
                else:
                    self.status[idx] = ""
                self.statchange(idx)
            self.rowmap = param.params.db.objs.keys()
            self.rowmap[:0] = self.objs.keys()
        else:
            self.edits = {}
            self.objs = {}
            for k in self.status.keys():
                if k < 0:
                    del self.status[k]
                    del self.istatus[k]
                else:
                    if 'C' in self.status[k]:
                        self.status[k] = "C"
                    else:
                        self.status[k] = ""
                    self.statchange(k)
            self.rowmap = param.params.db.objs.keys()
        self.adjustSize()

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
                c1 = self.coff + param.params.db.fldmap[f]['objidx']
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
            (idx, f) = self.index2db(index)
            col = index.column()
            if col < self.coff:
                if idx == 0:
                    if not f in self.defflds:
                        flags = flags | QtCore.Qt.ItemIsEditable
                else:
                    if not f in self.fixflds:
                        flags = flags | QtCore.Qt.ItemIsEditable
            else:
                if (idx != 0 or not f in self.defflds) and param.params.db.objflds[col-self.coff]['obj']:
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
