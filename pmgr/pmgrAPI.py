from .pmgrobj import pmgrobj

class pmgrAPI(object):
    def __init__(self, table, hutch):
        self.hutch = hutch.upper()
        self.pm = pmgrobj(table, hutch)

    @staticmethod
    def _search(dl, f, v):
        for d in dl.values():
            if d[f] == v:
                return d
        raise Exception("%s not found!" % v)

    @staticmethod
    def _fixmutex(d, mutex):
        for c in mutex:
            if c != ' ':
                try:
                    del d[self.pm.objflds[ord[c]-65]['name']]
                except:
                    pass
        return d

    def update_db(self):
        self.pm.updateTables(self.pm.checkForUpdate())

    def get_config(self, pv):
        self.update_db()
        d = self._search(self.pm.objs, 'rec_base', pv)
        return self.pm.cfgs[d['config']]['name']

    def set_config(self, pv, cfgname, o=None):
        if o is None:
            self.update_db()
            o = self._search(self.pm.objs, 'rec_base', pv)
        d = self._search(self.pm.cfgs, 'name', cfgname)
        self.pm.start_transaction()
        self.pm.objectChange(o['id'], {'config': d['id']})
        el = self.pm.end_transaction()
        if el != []:
            raise Exception("DB Errors", el)

    def apply_config(self, pv, cfgname=None):
        self.update_db()
        o = self._search(self.pm.objs, 'rec_base', pv)
        if cfgname is not None:
            self.set_config(pv, cfgname, o=o)
            self.update_db()
        self.pm.applyConfig(o['id'])

    def diff_config(self, pv, cfgname=None):
        self.update_db()
        o = self._search(self.pm.objs, 'rec_base', pv)
        if cfgname is None:
            cfgidx = None
        else:
            cfgidx = self._search(self.pm.cfgs, 'name', cfgname)['id']
        return self.pm.diffConfig(o['id'], cfgidx)

    def save_config(self, pv, cfgname=None, overwrite=False, parent=None):
        self.update_db()
        o = self._search(self.pm.objs, 'rec_base', pv)
        if cfgname is None:
            # Default to overwriting the existing configuration.
            do = self.pm.cfgs[o['config']]
            cfgname = do['name']
            overwrite = True
        else:
            try:
                do = self._search(self.pm.cfgs, 'name', cfgname)
            except:
                do = None
                overwrite = False
            if do is not None and not overwrite:
                raise Exception("Configuration %s already exists!" % cfgname)
        d = self.pm.getActualConfig(o['id'])
        if overwrite:
            d = self._fixmutex(d, do['mutex'])
            self.pm.start_transaction()
            self.pm.configChange(o['config'], d)
            el = self.pm.end_transaction()
            if el != []:
                raise Exception("DB Errors", el)
        else:
            # Add a new configuration
            if parent is None:
                parent = self.hutch
            p = self._search(self.pm.cfgs, 'name', parent)
            d['mutex'] = p['mutex']
            d['config'] = p['id']
            d = self._fixmutex(d, p['mutex'])
            d['name'] = cfgname
            self.pm.start_transaction()
            self.pm.configInsert(d)
            el = self.pm.end_transaction()
            if el != []:
                raise Exception("DB Errors", el)
            self.set_config(pv, cfgname)

    def match_config(self, pattern, substr=True, ci=True):
        self.update_db()
        return self.pm.matchConfigs(pattern, substr, ci)

