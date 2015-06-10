from PyQt4 import QtGui, QtCore
import param
import utils
import colmgr
import datetime
import utils
import pyca

class ObjModel(QtGui.QStandardItemModel):
    cname   = ["Status", "Name", "Config", "PV Base", "Owner", "Config Mode", "Comment"]
    cfld    = ["status", "name", "cfgname", "rec_base", "owner", "category", "comment"]
    ctips   = ["C = All PVs Connected\nD = Deleted\nM = Modified\nN = New\nX = Inconsistent",
               "Object Name", "Configuration Name", "PV Base Name", "Owner", None, None]
    coff    = len(cname)
    statcol = 0
    namecol = 1
    cfgcol  = 2
    pvcol   = 3
    owncol  = 4
    catcol  = 5
    comcol  = 6
    mutable = 2  # The first non-frozen column
    fixflds = ["status", "cfgname", "owner"]
    
    def __init__(self):
        QtGui.QStandardItemModel.__init__(self)
        self.pvdict = {}
        self.edits = {}
        self.objs = {}
        self.status = {}
        self.istatus = {}
        self.nextid = -1
        self.selrow = -1
        self.track = False
        self.lastsort = (0, QtCore.Qt.DescendingOrder)
        # Setup headers
        self.colcnt = len(param.params.pobj.objflds) + self.coff
        self.setColumnCount(self.colcnt)
        self.setRowCount(len(param.params.pobj.objs))
        self.rowmap = param.params.pobj.objs.keys()
        font = QtGui.QFont()
        font.setBold(True)
        for c in range(self.colcnt):
            if c < self.coff:
                i = QtGui.QStandardItem(self.cname[c])
                if self.ctips[c] != None:
                    i.setToolTip(self.ctips[c])
            else:
                i = QtGui.QStandardItem(param.params.pobj.objflds[c-self.coff]['alias'])
                desc = param.params.pobj.objflds[c-self.coff]['tooltip']
                if desc != "":
                    i.setToolTip(desc)
            self.setHorizontalHeaderItem(c, i)
        self.createStatus()
        self.connectAllPVs()

        self.connect(self, QtCore.SIGNAL("layoutAboutToBeChanged()"), self.doShowAll)
        self.connect(self, QtCore.SIGNAL("layoutChanged()"), self.doShow)

    def createStatus(self):
        for d in param.params.pobj.objs.values():
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
            return (self.rowmap[index.row()], param.params.pobj.objflds[c-self.coff]['fld'])

    def getObj(self, idx):
        if idx >= 0:
            return param.params.pobj.objs[idx]
        else:
            return self.objs[idx]

    def setCfg(self, idx, cfg):
        self.setValue(idx, 'cfgname', cfg)
        try:
            index = self.index(self.rowmap.index(idx), self.cfgcol)
            self.dataChanged.emit(index, index)
        except:
            pass

    def getCfg(self, idx, f, GetEdit=True):
        if GetEdit:
            try:
                return self.edits[idx][f]
            except:
                pass
        if f in self.cfld or f == 'mutex' or f == 'config':
            return self.getObj(idx)[f]
        elif param.params.pobj.fldmap[f]['obj']:
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
            if f in self.cfld or param.params.pobj.fldmap[f]['obj']:
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
            except:
                pass
        else:   # QtCore.Qt.EditRole
            try:
                v = self.edits[idx][f]
            except:
                if v2 != None:
                    v = v2
        # DisplayRole or EditRole fall through... v has our value!
        if f == 'category':
            v = param.params.catenum2[param.params.catenum.index(v)]
        return QtCore.QVariant(v)

    def setValue(self, idx, f, v):
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
        if f == 'category':
            v = param.params.catenum[param.params.catenum2.index(v)]
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
            cm = chr(param.params.pobj.fldmap[f]['colorder']+0x40)
            if cm in mutex:
                i = mutex.find(cm)
                self.promote(idx, f, i, mutex)
        except:
            pass

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
        
        self.setValue(idx, f, v)
        
        if f == 'rec_base':
            self.connectPVs(idx)
            r = index.row()
            self.dataChanged.emit(self.index(r, 0), self.index(r, self.colcnt - 1))
        else:
            self.dataChanged.emit(index, index)
        return True

    def promote(self, idx, f, setidx, curmutex):
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
        cm = chr(param.params.pobj.fldmap[derived]['colorder']+0x40)
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
            f = param.params.pobj.objflds[c-self.coff]['fld']
        try:
            return self.edits[idx][f]
        except:
            try:
                return self.getObj(idx)[f]
            except:
                return ""

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
        d['connstat'] = len(param.params.pobj.objflds)*[False]
        self.status[idx] = self.status[idx].replace("C", "")
        if base != "":
            for ofld in param.params.pobj.objflds:
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
            idx = param.params.pobj.fldmap[pv.fld]['objidx']
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
        utils.fixName(param.params.pobj.objs.values(), idx, name)
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
        db = param.params.pobj
        try:
            (idx, f) = self.index2db(index)
            flist = [f]
        except:
            idx = self.rowmap[index]
            flist = [d['fld'] for d in param.params.pobj.objflds if d['obj'] == True]
        for f in flist:
            if idx < 0:
                try:
                    vc = self.objs[idx]['_val'][f]
                except:
                    pass
                try:
                    va = self.objs[idx][f]
                except:
                    pass
            else:
                try:
                    vc = self.edits[idx][f]
                except:
                    try:
                        vc = db.objs[idx]['_val'][f]
                    except:
                        return False
                try:
                    va = db.objs[idx][f]
                except:
                    return False
            try:
                if db.fldmap[f]['obj'] and not param.equal(va, vc) and vc != None:
                    return True
            except:
                pass
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
                       lambda table, index: index.row() >= 0 and
                       self.rowmap[index.row()] != 0 and self.haveObjPVDiff(index))
        menu.addAction("Set all from PV", self.setAllFromPV,
                       lambda table, index: index.row() >= 0 and
                       self.rowmap[index.row()] != 0 and self.haveObjPVDiff(index.row()))
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
        menu.addAction("Auto config this object", self.autoone, self.testAuto)
        menu.addAction("Auto config all", self.autoall)
        table.addContextMenu(menu)
        colmgr.addColumnManagerMenu(table)

    def testAuto(self, table, index):
        try:
            idx = self.rowmap[index.row()]
            return self.getCfg(idx, 'category', True) == 'Auto' and 'C' in self.getStatus(idx)
        except:
            return False
    
    def setFromPV(self, table, index):
        (idx, f) = self.index2db(index)
        if idx >= 0:
            self.setData(index, QtCore.QVariant(param.params.pobj.objs[idx][f]))
        else:
            self.setData(index, QtCore.QVariant(self.objs[idx][f]))

    def setAllFromPV(self, table, index):
        db = param.params.pobj
        (idx, f) = self.index2db(index)
        flist = [(d['fld'], self.coff + d['objidx']) for d in param.params.pobj.objflds if d['obj'] == True]
        for (f, c) in flist:
            if idx >= 0:
                va = param.params.pobj.objs[idx][f]
                try:
                    vc = self.edits[idx][f]
                except:
                    vc = db.objs[idx]['_val'][f]
            else:
                va = self.objs[idx][f]
                vc = self.objs[idx]['_val'][f]
            if vc != None:
                self.setData(self.index(index.row(), c), QtCore.QVariant(va))
        
    def create(self, table, index):
        idx = self.nextid;
        self.nextid -= 1
        now = datetime.datetime.now()
        d = dict(param.params.pobj.objs[0])
        del d['_val']
        del d['connstat']
        dd = {'id': idx, 'config': 0, 'owner': param.params.hutch, 'name': "NewObject%d" % idx,
              'rec_base': "", 'dt_created': now, 'dt_updated': now, 'category': 'Manual',
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

    def checkSetMutex(self, d, e):
        for s in param.params.pobj.setflds:
            f = param.params.pobj.fldmap[s[0]]
            if not f['setmutex'] or not f['obj']:
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
    def commit(self, idx):
        d = self.getObj(idx)
        try:
            name = self.edits[idx]['name']
        except:
            name = d['name']
        if not utils.permission(d['owner'], None):
            param.params.pobj.transaction_error("Not Authorized to Change %s!" % name)
            return
        if name[0:10] == "NewObject-":
            param.params.pobj.transaction_error("Object cannot be named %s!" % name)
            return
        if 'D' in self.status[idx]:
            param.params.pobj.objectDelete(idx)
        else:
            try:
                e = self.edits[idx]
            except:
                e = {}
            try:
                if e['config'] < 0:
                    param.params.pobj.transaction_error("New configuration must be committed before committing %s!" % name)
                    return
            except:
                pass
            s = self.checkSetMutex(d, e)
            if s != []:
                param.params.pobj.transaction_error("Object %s does not have unique values for %s!" %
                                                  (name, str(s)))
                return
            if 'N' in self.status[idx]:
                newidx = param.params.pobj.objectInsert(param.params.doMap(self.getObj(idx)['_val']))
                if newidx != None:
                    param.params.db.addObjMap(idx, newidx)
            elif 'M' in self.status[idx]:
                param.params.pobj.objectChange(idx, param.params.doMap(self.edits[idx]))

    #
    # Note: this calls commit (and checks permissions!) even if no change!
    #
    def commitone(self, table, index):
        param.params.db.start_transaction()
        (idx, f) = self.index2db(index)
        self.commit(idx)
        if param.params.db.end_transaction():
            self.objChangeDone(idx)
            return True
        else:
            return False

    #
    # Note: this only calls commit for changes!
    #
    def commitall(self):
        if not param.params.cfgmodel.confirmCommit():
            return False
        param.params.db.start_transaction()
        for (idx, s) in self.status.items():
            if 'D' in s:
                self.commit(idx)
        param.params.cfgmodel.commitall(False)
        param.params.grpmodel.commitall(False)
        for (idx, s) in self.status.items():
            if ('N' in s or 'M' in s) and not 'D' in s:  # Paranoia.  We should never have DM or DN.
                self.commit(idx)
        if param.params.db.end_transaction(): 
            param.params.cfgmodel.cfgChangeDone()
            self.objChangeDone()
            return True
        else:
            return False

    def revertall(self):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        for idx in self.edits.keys():
            try:
                del self.edits[idx]
            except:
                pass
            self.status[idx] = self.status[idx].replace("M", "")
        self.emit(QtCore.SIGNAL("layoutChanged()"))
        param.params.cfgmodel.revertall()
        param.params.grpmodel.revertall()

    def apply(self, idx):
        d = self.getObj(idx)
        pvd = self.pvdict[idx]
        for s in param.params.pobj.setflds:
            for f in s:
                if param.params.pobj.fldmap[f]['writezero']:
                    try:
                        v = d[f]             # PV value
                    except:
                        continue
                    v2 = self.getCfg(idx, f) # Configured value
                    #
                    # Write a value if:
                    #     1. It's not derived (the value isn't None), and either
                    #     2a. It's a change, or
                    #     2b. It's a "must write" value.
                    #
                    if v2 != None and (not param.equal(v, v2) or param.params.pobj.fldmap[f]['mustwrite']):
                        try:
                            z = param.params.pobj.fldmap[f]['enum'][0]
                        except:
                            z = 0
                        try:
                            pv = pvd[f]
                            if param.params.debug:
                                print "Put %s to %s" % (str(z), pv.name)
                            else:
                                pv.put(z, -1.0)
                        except:
                            pass
            pyca.flush_io()
            for f in s:
                try:
                    v = d[f]             # PV value
                except:
                    continue
                v2 = self.getCfg(idx, f) # Configured value
                if v2 != None and (not param.equal(v, v2) or param.params.pobj.fldmap[f]['mustwrite']):
                    try:
                        pv = pvd[f]
                        if param.params.debug:
                            print "Put %s to %s" % (str(v2), pv.name)
                        else:
                            pv.put(v2, -1.0)
                    except:
                        pass
            pyca.flush_io()

    #
    # Note: commitone always calls commit, and that does the permission check!
    #
    def applyone(self, table, index):
        if self.commitone(table, index):
            (idx, f) = self.index2db(index)
            self.apply(idx)

    #
    # If there are no changes, commitall does not do a permission check, so we need
    # to do one.
    #
    def applyall(self):
        if not self.commitall():
            return
        if not utils.permission(param.params.hutch, None):
            QtGui.QMessageBox.critical(None, "Error", "Not authorized to apply changes!",
                                       QtGui.QMessageBox.Ok)
            return
        for idx in self.rowmap:
            self.apply(idx)

    def revertone(self, table, index):
        (idx, f) = self.index2db(index)
        try:
            del self.edits[idx]
        except:
            pass
        self.status[idx] = self.status[idx].replace("M", "")
        row = self.rowmap.index(idx)
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.colcnt - 1))

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
            self.rowmap = param.params.pobj.objs.keys()
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
            self.rowmap = param.params.pobj.objs.keys()
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
                c1 = self.coff + param.params.pobj.fldmap[f]['objidx']
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
                if idx != 0 and not f in self.fixflds:
                    flags = flags | QtCore.Qt.ItemIsEditable
            else:
                if idx != 0 and param.params.pobj.objflds[col-self.coff]['obj']:
                    flags = flags | QtCore.Qt.ItemIsEditable
        return flags

    def editorInfo(self, index):
        c = index.column()
        if c == self.catcol:
            return param.params.catenum2
        if c < self.coff:
            return str
        try:
            return param.params.pobj.objflds[c - self.coff]['enum']
        except:
            return param.params.pobj.objflds[c - self.coff]['type']

    def doShow(self):
        ui = param.params.ui
        v = []
        if ui.actionAuto.isChecked():
            v.append("Auto")
        if ui.actionManual.isChecked():
            v.append("Manual")
        if ui.actionProtected.isChecked():
            v.append("Protected")
        for i in range(len(self.rowmap)):
            # Sometimes, we get a little ahead of ourselves after a deletion and this fails.
            # However, we'll get the *real* update soon enough, so just stop the error.
            try:
                if self.rowmap[i] == 0 or self.getCfg(self.rowmap[i], 'category', True) in v:
                    param.params.ui.objectTable.setRowHidden(i, False)
                else:
                    param.params.ui.objectTable.setRowHidden(i, True)
            except:
                pass

    def doShowAll(self):
        for i in range(len(self.rowmap)):
            param.params.ui.objectTable.setRowHidden(i, False)

    def doTrack(self):
        self.track = param.params.ui.actionTrack.isChecked()
        if self.track and self.selrow >= 0:
            param.params.cfgmodel.selectConfig(self.getCfg(self.rowmap[self.selrow], 'config', True))

    def selectionChanged(self, selected, deselected):
        if not selected.isEmpty():
            i = selected.indexes()[0];
            self.selrow = i.row()
        else:
            self.selrow = -1
        if self.track and self.selrow >= 0:
            param.params.cfgmodel.selectConfig(self.getCfg(self.rowmap[self.selrow], 'config', True))

    def getObjSel(self):
        ui = param.params.ui
        d = {True: "1", False: "0"}
        v = ""
        v += d[ui.actionAuto.isChecked()]
        v += d[ui.actionProtected.isChecked()]
        v += d[ui.actionManual.isChecked()]
        v += d[ui.actionTrack.isChecked()]
        return v

    def setObjSel(self, v):
        if v != "" and v != None:
            ui = param.params.ui
            d = {"1" : True, "0": False}
            ui.actionAuto.setChecked(d[v[0]])
            ui.actionProtected.setChecked(d[v[1]])
            ui.actionManual.setChecked(d[v[2]])
            ui.actionTrack.setChecked(d[v[3]])
            self.doShow()
            self.doTrack()

    def doAuto(self, idx):
        d = param.params.pobj.getAutoCfg(self.getObj(idx))
        for (k, v) in d.iteritems():
            if v != None:
                self.setValue(idx, k, v)

    def autoone(self, table, index):
        (idx, f) = self.index2db(index)
        self.doAuto(idx)
        self.dataChanged.emit(self.index(index.row(), 0), self.index(index.row(), self.colcnt - 1))

    def autoall(self, table, index):
        for r in range(len(self.rowmap)):
            idx = self.rowmap[r]
            if self.getCfg(idx, 'category', True) == "Auto" and 'C' in self.getStatus(idx):
                self.doAuto(idx)
                self.dataChanged.emit(self.index(r, 0), self.index(r, self.colcnt - 1))

    def getObjName(self, idx):
        try:
            return self.edits[idx]['name']
        except:
            return self.getObj(idx)['name']

    def getObjList(self, types=None):
        if types == None:
            types = param.params.catenum
        return [self.getObjName(idx) for idx in self.rowmap
                if self.getCfg(idx, 'category', True) in types]

    def getObjId(self, name):
        for i in self.rowmap:
            if self.getObjName(i) == name:
                return i
        return 0

    def cfgrenumber(self, old, new):
        for d in self.edits.values():
            try:
                if d['config'] == old:
                    d['config'] = new
            except:
                pass
        for d in self.objs.values():
            if d['config'] == old:
                d['config'] = new
