from .pmgrobj import pmgrobj

class pmgrAPI(object):
    """
    An application interface to the parameter manager.

    Parameters
    ----------
    table : str
        The type of object being configured.  (Probably "ims_motor".)

    hutch : str
        The name of the hutch used to retrieve objects from the database.
    """
    def __init__(self, table, hutch):
        self.hutch = hutch.upper()
        self.pm = pmgrobj(table, hutch)

    @staticmethod
    def _search(dl, f, v):
        """
        A private search method.

        Parameters
        ----------
        dl : list
            A list of dictionaries to be searched.

        f : str
            The key in the dictionary to match.

        v : any
            The value in the dictionary to match.

        Returns
        -------
        match : dict
            Returns the dictionary in the list with the matching value
            of the field.  Raises an exception if no match.
        """
        for d in dl.values():
            if d[f] == v:
                return d
        raise Exception("%s not found!" % v)

    @staticmethod
    def _fixmutex(d, mutex):
        """
        A private method to fix the configuration fields to match the 
        mutex condition.

        The "mutex" field is slightly complicated.  The general idea is
        that there can be sets of fields that when you set all but one
        field in the set, the remaining field is calculated from the 
        others.  For each such set, the "mutex" string indicates which
        field is the derived one.  (Derived fields should not have values
        assigned in the database.)

        Parameters
        ----------
        d : dict
            A configuration dictionary.

        mutex: str
            A string with one character per mutex set.  The character 
            is a space if this set is not used.  Otherwise, the character
            encodes a field identified by column order, chr(colorder + 64).

        Returns
        -------
        d : dict
            The original configuration dictionary with the derived fields
            removed.
        """
        for c in mutex:
            if c != ' ':
                try:
                    del d[self.pm.objflds[ord[c]-65]['name']]
                except:
                    pass
        return d

    def update_db(self):
        """
        Re-read the configuration database, if needed.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        self.pm.updateTables(self.pm.checkForUpdate())

    def get_config(self, pv):
        """
        Get the name of the configuration associated with a given PV base.

        Parameters
        ----------
        pv : str
            The base pvname to use in the lookup.

        Returns
        -------
        config : str
            The name of the configuration associated with the PV.

        Throws an exception if the PV is not in the database.
        """
        self.update_db()
        d = self._search(self.pm.objs, 'rec_base', pv)
        return self.pm.cfgs[d['config']]['name']

    def set_config(self, pv, cfgname, o=None):
        """
        Set the configuration for a given PV base.

        Parameters
        ----------
        pv : str
            The base pvname.

        config : str
            The name of the configuration to assign.

        Returns
        -------
        Nothing.  Raises an exception if the assignment fails for any reason.
        """
        #
        # NOTE: o is a private parameter.  It is an object dictionary for the pv,
        # and is used internally to avoid an extra update and lookup.
        # 
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
        """
        Apply the configuration for a given PV base.

        Parameters
        ----------
        pv : str
            The base pvname.

        config : str
            The name of the configuration to assign.  If this is None,
            use the default configuration in the database.

        Returns
        -------
        Nothing.  Raises an exception if the application fails for any reason.
        """
        self.update_db()
        try:
            # See if the object is in the database.
            o = self._search(self.pm.objs, 'rec_base', pv)
        except:
            # It isn't.  So use the alternative form of applyConfig.
            c = self._search(self.pm.cfgs, 'name', cfgname)
            self.pm.applyConfig(pv, cfg=c['id'])
            return
        # The object is in the database!  Set its config, and apply!
        if cfgname is not None:
            self.set_config(pv, cfgname, o=o)
            self.update_db()
        self.pm.applyConfig(o['id'])

    def diff_config(self, pv, cfgname=None):
        """
        Find the differences between the actual motor settings and the
        configuration.

        Parameters
        ----------
        pv : str
            The base pvname.

        cfgname : str
            The name of the configuration to compare the settings to.  If
            this is None, use the default configuration in the database.

        Returns
        -------
        diff : dict
            A dictionary mapping field names to (actual, config) tuples of
            differing values.

        Raises an exception if the comparison fails for any reason.
        """
        self.update_db()
        o = self._search(self.pm.objs, 'rec_base', pv)
        if cfgname is None:
            cfgidx = None
        else:
            cfgidx = self._search(self.pm.cfgs, 'name', cfgname)['id']
        return self.pm.diffConfig(o['id'], cfgidx)

    def save_config(self, pv, cfgname=None, overwrite=False, parent=None):
        """
        Save the current motor settings into the database.

        Parameters
        ----------
        pv : str
            The base pvname to save.

        cfgname : str
            The name of the configuration to save.  If this is None, use
            the default configuration in the database.  If this is not
            None, change the motor entry to use the new configuration
            after it is saved.

        overwrite : boolean
            If cfgname is not None and is an existing configuration, 
            overwrite it if this is True, otherwise throw an exception.

        parent : str
            The name of the parent configuration, if this is a new 
            configuration.  If this is None, default to the uppercase
            hutch name.

        Returns
        -------
        Nothing.  Raises an exception if the this fails for any reason.
        """
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
        """
        Find configurations that match a given pattern.

        Parameters
        ----------
        pattern : str
            The pattern to look for.  "." matches any character, and "*"
            matches any string.  These may be quoted with "\".

        substr : boolean
            If True, match a substring, otherwise match the entire
            configuration name.  (Default to True.)

        ci : boolean
            If True, do a case insensitive match, otherwise be case
            sensitive.  (Default to True.)

        Returns
        -------
        clist : list
            A list of configuration names (strings) that match the pattern.

        Throws an exception if there is a database problem.
        """
        self.update_db()
        return self.pm.matchConfigs(pattern, substr, ci)

