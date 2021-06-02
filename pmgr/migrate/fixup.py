#!/usr/bin/env python
import pmgrobj
import sys

#from pmgrobj import pmgrobj

# Check the raw object for number of Nones:
#     0         - Everything specified, take one at random
#     1         - That's our winner.
#     2 or more - Check the inherited config the same way, 
#                 except two or more is an error!
def assign_mutex(p, cfg, m, full, cm):
    ff = []
    for f in p.mutex_sets[m]:
        if cfg[f] is None:
            ff.append(f)
    if len(ff) >= 2:
        ff = []
        for f in p.mutex_sets[m]:
            if full[f] is None:
                ff.append(f)
    if len(ff) >= 2:
        raise Exception("A: cfg %d has too many nulls for mutex %s." % (i, p.mutex_sets[m]))
    if len(ff) == 0:
        if cm == ' ':
            f = p.mutex_sets[m][0]
        else:
            f = p.objflds[ord(cm)-0x41]['fld']
    else:
        f = ff[0]
    return f

def main():
    prod = None
    for a in sys.argv:
        if a == '--prod':
            prod = True
        elif a == '--dev':
            prod = False
    if prod is None:
        print("Usage: fixup [--prod | --dev]")
        sys.exit(0)
    p = pmgrobj.pmgrobj('ims_motor', None, prod=prod)
    # Fixup the mutex field in configurations, and build out the configuration with
    # no inheritance.
    for i in p.cfgs.keys():
        full = p.getConfig(i)
        e = {}
        for f in full['_haveval'].keys():
            if not full['_haveval'][f] and full[f] is not None:
                e[f] = full[f]
        cm = list(full['curmutex'])
        for m in range(len(p.mutex_obj)):
            if p.mutex_obj[m]:
                cm[m] = ' '
            elif cm[m] == ' ':
                f = assign_mutex(p, p.cfgs[i], m, full, cm[m])
                cm[m] = chr(p.fldmap[f]['colorder'] + 0x40)
                #print("cfg %i is setting %f to None" % (i, f))
                if p.cfgs[i][f] is not None:
                    e[f] = None
            else:
                # Make sure this is actually None, but the others aren't!
                ff = p.objflds[ord(cm[m])-0x41]['fld']
                for f in p.mutex_sets[m]:
                    if f == ff:
                        if full[f] is not None:
                            #print("cfg %d has a value for %s." % (i, f))
                            f = assign_mutex(p, p.cfgs[i], m, full, cm[m])
                            cm[m] = chr(p.fldmap[f]['colorder'] + 0x40)
                            if p.cfgs[i][f] is not None:
                                e[f] = None
                            break
                    else:
                        if full[f] is None:
                            #print("cfg %d has too many nulls for mutex %s." % (i, p.mutex_sets[m]))
                            f = assign_mutex(p, p.cfgs[i], m, full, cm[m])
                            cm[m] = chr(p.fldmap[f]['colorder'] + 0x40)
                            if p.cfgs[i][f] is not None:
                                e[f] = None
                            break
        full['curmutex'] = "".join(cm)        
        if full['curmutex'] != full['mutex']:
            e['mutex'] = full['curmutex']
        if e != {}:
            p.configChange(i, e, False)
    # Fixup the mutex field in objects.
    for i in p.objs.keys():
        cm = list(p.objs[i]['mutex'])
        e = {}
        for m in range(len(p.mutex_obj)):
            if not p.mutex_obj[m]:
                cm[m] = ' '
            elif cm[m] == ' ':
                f = assign_mutex(p, p.objs[i], m, p.objs[i], cm[m])
                if p.objs[i][f] is not None:
                    e[f] = None
                cm[m] = chr(p.fldmap[f]['colorder'] + 0x40)
            else:
                # Make sure this is actually None, but the others aren't!
                ff = p.objflds[ord(cm[m])-0x41]['fld']
                for f in p.mutex_sets[m]:
                    if f == ff:
                        if p.objs[i][f] is not None:
                            #print("cfg %d has a value for %s." % (i, f))
                            f = assign_mutex(p, p.objs[i], m, p.objs[i], cm[m])
                            cm[m] = chr(p.fldmap[f]['colorder'] + 0x40)
                            if p.objs[i][f] is not None:
                                e[f] = None
                            break
                    else:
                        if p.objs[i][f] is None:
                            #print("cfg %d has too many nulls for mutex %s." % (i, p.mutex_sets[m]))
                            f = assign_mutex(p, p.objs[i], m, p.objs[i], cm[m])
                            cm[m] = chr(p.fldmap[f]['colorder'] + 0x40)
                            if p.objs[i][f] is not None:
                                e[f] = None
                            break
        newmutex = "".join(cm)
        if p.objs[i]['mutex'] != newmutex:
            e['mutex'] = newmutex
        if p.objs[i]['category'] == 'Auto':
            e['category'] = 'Manual'
        if e != {}:
            p.objectChange(i, e, False)
    # Make sure all objects have a base PV, and all base PVs are unique.
    # Delete duplicates arbitrarily.
    rdict={}
    for (k, v) in p.objs.items():
        try:
            rdict[v['rec_base']].append(v['id'])
        except:
            rdict[v['rec_base']] = [v['id']]
    for (k, v) in rdict.items():
        if len(v) > 1:
            for i in v[1:]:
                p.objectDelete(i)
    p.con.commit()

if __name__ == '__main__':
    main()

