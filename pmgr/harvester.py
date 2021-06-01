#!/usr/bin/env python
#
# A bizarre combination of code from IocManager, the parent/child IOC compilation process, and
# ParameterManager.
#
import fcntl, re, sys, ast, os, operator
from io import StringIO

from psp.options import Options
from psp.Pv import Pv
import pyca

from .pmgrobj import pmgrobj


CONFIG_FILE    = "/reg/g/pcds/pyps/config/%s/iocmanager.cfg"
EPICS_TOP      = "/reg/g/pcds/package/epics/"
EPICS_SITE_TOP = "/reg/g/pcds/package/epics/3.14/"

hutch = None
fldlist = { 'FLD_HLM',
            'FLD_HOMD',
            'FLD_LLM',
            'FLD_OFF',
            'FLD_DESC' };

def caget(pvname,timeout=30.0):
    try:
        pv = Pv(pvname)
        pv.connect(timeout)
        pv.get(ctrl=False, timeout=timeout)
        v = pv.value
        pv.disconnect()
        return v
    except pyca.pyexc as e:
        print('pyca exception: %s' %(e))
        return None
    except pyca.caexc as e:
        print('channel access exception: %s' %(e))
        return None

def readConfig():
    config = {'procmgr_config': None, 'hosts': None, 'dir':'dir',
              'id':'id', 'cmd':'cmd', 'flags':'flags', 'port':'port', 'host':'host',
              'disable':'disable', 'history':'history', 'delay':'delay', 'alias':'alias' }
    vars = set(config.keys())
    cfgfn = CONFIG_FILE % hutch
    f = open(cfgfn, "r")
    fcntl.lockf(f, fcntl.LOCK_SH)    # Wait for the lock!!!!
    try:
        execfile(cfgfn, {}, config)
        res = config['procmgr_config']
    except:
        res = None
    fcntl.lockf(f, fcntl.LOCK_UN)
    f.close()
    if res == None:
        return None
    d = []
    for l in res:
        if 'disable' in l.keys() and l['disable']:
            continue
        name = l['id']
        dir  = l['dir']
        if re.search("/ims/", dir) or re.search("/ims$", dir):
            if dir[0:3] == "../":
                dir = EPICS_TOP + dir[3:]
            elif dir[0] != '/':
                dir = EPICS_SITE_TOP + dir
            d.append((name, dir))
    return d

class config():
    def __init__(self):
        self.path = os.getcwd()
        self.dirname = self.path.split('/')[-1]
        self.ddict = {}
        self.idict = {}

        # Pre-define some regular expressions!
        self.doubledollar = re.compile("^(.*?)\$\$")
        self.keyword      = re.compile("^(UP|LOOP|IF|INCLUDE|TRANSLATE|COUNT)\(|^(CALC)\{")
        self.parens       = re.compile("^\(([^)]*?)\)")
        self.brackets     = re.compile("^\{([^}]*?)\}")
        self.trargs       = re.compile('^\(([^,]*?),"([^"]*?)","([^"]*?)"\)')
        self.ifargs       = re.compile('^\(([^,)]*?),([^,)]*?),([^,)]*?)\)')
        self.word         = re.compile("^([A-Za-z0-9_]*)")
        self.operators = {ast.Add: operator.add,
                          ast.Sub: operator.sub,
                          ast.Mult: operator.mul,
                          ast.Div: operator.truediv,
                          ast.Pow: operator.pow,
                          ast.LShift : operator.lshift,
                          ast.RShift: operator.rshift,
                          ast.BitOr: operator.or_,
                          ast.BitAnd : operator.and_,
                          ast.BitXor: operator.xor}

    def create_instance(self, iname, id, idict, ndict):
        try:
            allinst = idict[iname]
        except:
            allinst = []
            idict[iname] = []
        n = str(len(allinst))
        if id != None:
            ndict[id] = (iname, int(n))
        dd = {}
        dd["INDEX"] = n
        return (dd, n)

    def finish_instance(self, iname, idict, dd):
        idict[iname].append(dd)

    def read_config(self, file, extra):
        w       = re.compile("^[ \t]*([^ \t=]+)")
        wq      = re.compile('^[ \t]*"([^"]*)"')
        wqq     = re.compile("^[ \t]*'([^']*)'")
        assign  = re.compile("^[ \t]*=")
        sp      = re.compile("^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]+(.+?)[ \t]*$")
        spq     = re.compile('^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]+"([^"]*)"[ \t]*$')
        spqq    = re.compile("^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]+'([^']*)'[ \t]*$")
        eq      = re.compile("^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*(.*?)[ \t]*$")
        eqq     = re.compile('^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*"([^"]*)"[ \t]*$')
        eqqq    = re.compile("^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*'([^']*)'[ \t]*$")
        inst    = re.compile("^[ \t]*(([A-Za-z_][A-Za-z0-9_]*):[ \t]*)?([A-Za-z_][A-Za-z0-9_]*)\((.*)\)[ \t]*$")
        inst2    = re.compile("^[ \t]*INSTANCE[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*([A-Za-z0-9_]*)[ \t]*$")

        prminst = re.compile("^([A-Za-z_][A-Za-z0-9_]*)(,)")
        prmidx  = re.compile("^([A-Za-z_][A-Za-z0-9_]*?)([0-9_]+)(,)")
        prmeq   = re.compile("^([A-Za-z_][A-Za-z0-9_]*)=([^,]*)(,)")
        prmeqq  = re.compile('^([A-Za-z_][A-Za-z0-9_]*)="([^"]*)"(,)')
        prmeqqq = re.compile("^([A-Za-z_][A-Za-z0-9_]*)='([^']*)'(,)")

        fp = open(file)
        if not fp:
            raise IOError("File %s not found!" % ( file ))
        lines = [l + "\n" for l in extra] + fp.readlines()
        fp.close()
        origlines = lines

        # Do the preliminary config expansion!
        output = StringIO.StringIO()
        expand(self, lines, output)
        value = output.getvalue()
        output.close()
        lines = value.split("\n")

        d = {"DIRNAME": self.dirname, "PATH" : self.path}
        for l in lines:
            l = l.strip()
            m = inst.search(l)
            if m != None:
                continue            # Skip instantiations for now!
            m = inst2.search(l)
            if m != None:           # First new-style instantiation --> we're done here!
                break
            # Search for a one-line assignment of some form!
            m = eqqq.search(l)
            if m == None:
                m = eqq.search(l)
                if m == None:
                    m = eq.search(l)
                    if m == None:
                        m = spqq.search(l)
                        if m == None:
                            m = spq.search(l)
                            if m == None:
                                m = sp.search(l)
            if m != None:
                var = m.group(1)
                val = m.group(2)
                d[var] = val;
                continue
            if l != "" and l[0] != '#':
                print("Skipping unknown line: %s" % l)
        self.ddict = d

        # Now that we have the aliases, reprocess the config!
        
        lines = origlines
        output = StringIO.StringIO()
        expand(self, lines, output)
        value = output.getvalue()
        output.close()
        lines = value.split("\n")
        
        i = {}
        d = {"DIRNAME": self.dirname, "PATH": self.path}
        nd = {}
        newstyle = False
        ininst   = False
        
        for l in lines:
            l = l.strip()
            m = inst2.search(l)
            if m != None:
                newstyle = True
            if newstyle:
                if m != None:
                    if ininst:
                        self.finish_instance(iname, i, dd)
                    ininst = True
                    iname = m.group(1)
                    id = m.group(2)
                    dd, n = self.create_instance(iname, id, i, nd)
                else:
                    loc = 0           # Look for parameters!
                    first = None
                    haveeq = False
                    while l[loc:] != '':
                        m = assign.search(l[loc:])
                        if m != None:
                            loc += m.end()
                            if haveeq:
                                print("Double equal sign in |%s|" % l)
                            haveeq = True
                            continue   # Just ignore it!

                        m = wqq.search(l[loc:])
                        if m != None:
                            loc += m.end()
                        else:
                            m = wq.search(l[loc:])
                            if m != None:
                                loc += m.end() + 1
                            else:
                                m = w.search(l[loc:])
                                if m != None:
                                    loc += m.end() + 1
                                else:
                                    break        # How does this even happen?!?
                        val = m.group(1)
                        if first != None:
                            dd[first] = val
                            d[iname + first + n] = val
                            first = None
                        else:
                            # Could this be an instance parameter?
                            useinst = ''
                            usenum  = 0
                            try:
                                t = nd[val]
                                useinst = t[0]
                                usenum = t[1]
                            except:
                                m = prmidx.search(val+",")
                                if m != None:
                                    useinst = m.group(1)
                                    usenum = int(m.group(2))
                            try:
                                used = i[useinst][usenum]
                                for k in used.keys():
                                    var = useinst + k
                                    val = used[k]
                                    dd[var] = val
                            except:
                                first = val
                                haveeq = False
                continue
            m = inst.search(l)
            if m != None:
                id = m.group(2)
                iname = m.group(3)
                params = m.group(4) + ","
                dd, n = self.create_instance(iname, id, i, nd)
                while (params != ""):
                    m = prmeqqq.search(params)
                    if m == None:
                        m = prmeqq.search(params)
                        if m == None:
                            m = prmeq.search(params)
                    if m != None:
                        # Parameter of the form VAR=VAL. Global dictionary will also
                        # get inameVARn=VAL.
                        var = m.group(1)
                        val = m.group(2)
                        dd[var] = val
                        d[iname + var + n] = val
                        params = params[m.end(3):len(params)]
                    else:
                        m = prminst.search(params)
                        if m != None:
                            # This is an instance parameter.  It is either old-style,
                            # INSTn, or an arbitrary name.  Check the name dict first!
                            try:
                                t = nd[m.group(1)]
                                useinst = t[0]
                                usenum = t[1]
                                params = params[m.end(2):len(params)]
                            except:
                                m = prmidx.search(params)
                                if m == None:
                                    print("Unknown parameter in line %s" % params)
                                    params = ""
                                    continue
                                useinst = m.group(1)
                                usenum = int(m.group(2))
                                params = params[m.end(3):len(params)]
                            # Find the instance, and add all of its named parameters
                            # VAL with the name INSTVAL.
                            used = i[useinst][usenum]
                            for k in used.keys():
                                var = useinst + k
                                val = used[k]
                                dd[var] = val
                        else:
                            print("Unknown parameter in line %s" % params)
                            params = ""
                self.finish_instance(iname, i, dd)
                continue
            # Search for a one-line assignment of some form!
            m = eqqq.search(l)
            if m == None:
                m = eqq.search(l)
                if m == None:
                    m = eq.search(l)
                    if m == None:
                        m = spqq.search(l)
                        if m == None:
                            m = spq.search(l)
                            if m == None:
                                m = sp.search(l)
            if m != None:
                var = m.group(1)
                val = m.group(2)
                d[var] = val;
                continue
            if l != "" and l[0] != '#':
                print("Skipping unknown line: %s" % l)
        if ininst:
            self.finish_instance(iname, i, dd)
        self.idict = i
        self.ddict = d

    def eval_expr(self, expr):
        return self.eval_(ast.parse(expr).body[0].value) # Module(body=[Expr(value=...)])

    def eval_(self, node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Name):
            try:
                x = int(self.ddict[node.id])
            except:
                x = 0
            return x
        elif isinstance(node, ast.operator):
            return self.operators[type(node)]
        elif isinstance(node, ast.BinOp):
            return self.eval_(node.op)(self.eval_(node.left), self.eval_(node.right))
        else:
            raise TypeError(node)


def expand(cfg, lines, f):
    i = 0
    loc = 0
    while i < len(lines):
        m = cfg.doubledollar.search(lines[i][loc:])
        if m == None:
            # Line without a $$.
            f.write("%s" % lines[i][loc:])
            i += 1
            loc = 0
            continue

        # Write the first part
        f.write(m.group(1))
        pos = loc + m.end(1)     # save where we found this!
        loc = pos + 2            # skip the '$$'!

        m = cfg.keyword.search(lines[i][loc:])
        if m != None:
            kw = m.group(1)
            if kw == None:
                kw = m.group(2)
                loc += m.end(2)      # Leave on the '{'!
            else:
                loc += m.end(1)      # Leave on the '('!
            
            if kw == "TRANSLATE":
                argm = cfg.trargs.search(lines[i][loc:])
                if argm != None:
                    loc += argm.end(3)+2
            elif kw == "CALC":
                argm = cfg.brackets.search(lines[i][loc:])
                if argm != None:
                    loc += argm.end(1)+1
            elif kw == "IF":
                argm = cfg.ifargs.search(lines[i][loc:])
                if argm != None:
                    kw = "TIF"    # Triple IF!
                    loc += argm.end(3)+1
                else:
                    argm = cfg.parens.search(lines[i][loc:])
                    if argm != None:
                        loc += argm.end(1)+1
                    if pos == 0 and lines[i][loc:].strip() == "":
                        # If the $$ directive is the entire line, don't add a newline!
                        loc = 0;
                        i += 1
            else:
                argm = cfg.parens.search(lines[i][loc:])
                if argm != None:
                    loc += argm.end(1)+1
                if pos == 0 and lines[i][loc:].strip() == "":
                    # If the $$ directive is the entire line, don't add a newline!
                    loc = 0;
                    i += 1
                    
            if argm != None:
                if kw == "LOOP":
                    iname = argm.group(1)
                    startloop = re.compile("(.*?)\$\$LOOP\(" + iname + "(\))")
                    endloop = re.compile("(.*?)\$\$ENDLOOP\(" + iname + "(\))")
                    t = searchforend(lines, endloop, startloop, endloop, i, loc)
                    if t == None:
                        print("Cannot find $$ENDLOOP(%s)?" % iname)
                        sys.exit(1)
                    if iname[0] >= "0" and iname[0] <= "9":
                        try:
                            cnt = int(iname)
                        except:
                            cnt = 0
                        ilist = [{"INDEX": str(n)} for n in range(cnt)]
                    elif iname in cfg.idict.keys():
                        try:
                            ilist = cfg.idict[iname]
                        except:
                            ilist = []
                    else:
                        try:
                            cnt = int(cfg.ddict[iname])
                        except:
                            cnt = 0
                        ilist = [{"INDEX": str(n)} for n in range(cnt)]
                    olddict = cfg.ddict
                    for inst in ilist:
                        cfg.ddict = rename_index(olddict.copy())
                        cfg.ddict.update(inst)
                        expand(cfg, t[0], f)
                    cfg.ddict = olddict
                    i = t[1]
                    loc = t[2]
                elif kw == "IF":
                    iname = argm.group(1)
                    ifre = re.compile("(.*?)\$\$IF\(" + iname + "(\))")
                    endre = re.compile("(.*?)\$\$ENDIF\(" + iname + "(\))")
                    elsere = re.compile("(.*?)\$\$ELSE\(" + iname + "(\))")
                    t = searchforend(lines, endre, ifre, endre, i, loc)
                    if t == None:
                        print("Cannot find $$ENDIF(%s)?" % iname)
                        sys.exit(1)
                    elset = searchforend(t[0], elsere, ifre, endre, 0, 0)
                    try:
                        v = cfg.ddict[iname]
                    except:
                        v = ""
                    if v != "":
                        # True, do the if!
                        if elset != None:
                            newlines = elset[0]
                        else:
                            newlines = t[0]
                        expand(cfg, newlines, f)
                    else:
                        # False, do the else!
                        if elset != None:
                            newlines = t[0][elset[1]:]
                            newlines[0] = newlines[0][elset[2]:]
                            expand(cfg, newlines, f)
                    i = t[1]
                    loc = t[2]
                elif kw == "TIF":
                    iname = argm.group(1)
                    newlines = []
                    try:
                        v = cfg.ddict[iname]
                    except:
                        v = ""
                    if v != "":
                        # True, do the if!
                        newlines.append(argm.group(2))
                    else:
                        # False, do the else!
                        newlines.append(argm.group(3))
                    expand(cfg, newlines, f)
                elif kw == "INCLUDE":
                    try:
                        fn = cfg.ddict[argm.group(1)]
                    except:
                        fn = argm.group(1)
                    try:
                        newlines=open(fn).readlines()
                        expand(cfg, newlines, f)
                    except:
                        print("Cannot open file %s!" % fn)
                elif kw == "COUNT":
                    try:
                        cnt = str(len(cfg.idict[argm.group(1)]))
                    except:
                        cnt = "0"
                    f.write(cnt)
                elif kw == "CALC":
                    # Either $$CALC{expr} or $$CALC{expr,format}.
                    args = argm.group(1).split(",")
                    output = StringIO.StringIO()
                    expand(cfg, [args[0]], output)
                    value = output.getvalue()
                    output.close()
                    if len(args) > 1:
                        fmt = args[1]
                    else:
                        fmt = "%d"
                    try:
                        v = cfg.eval_expr(value)
                    except:
                        v = 0
                    f.write(fmt % (v))
                elif kw == "UP":
                    try:
                        fn = cfg.ddict[argm.group(1)]
                    except:
                        fn = argm.group(1)
                    try:
                        f.write(fn[:fn.rindex('/')])
                    except:
                        pass
                else: # Must be "TRANSLATE"
                    try:
                        val = cfg.ddict[argm.group(1)].translate(string.maketrans(enumstring(argm.group(2)),
                                                                                  enumstring(argm.group(3))))
                        f.write(val)
                    except:
                        pass
            else:
                print("Malformed $$%s statement?" % kw)
                sys.exit(1)
            continue
        
        # Just a variable reference!
        if lines[i][loc] == "(":
            m = cfg.parens.search(lines[i][loc:])
        else:
            m = cfg.word.search(lines[i][loc:])
        if m != None:
            try:
                val = cfg.ddict[m.group(1)]
                f.write(val)
            except:
                pass
            if lines[i][loc] == '(':
                loc += m.end(1) + 1
            else:
                loc += m.end(1)
        else:
            print("Can't find variable name?!?")

def getMotorVals(pvbase):
    d = {}
    for f in fldlist:
        try:
            d[f] = caget(pvbase + "." + f[4:])
        except:
            d[f] = None
    return d

def makeMotor(ioc, pvbase, port, extra=""):
    d = getMotorVals(pvbase)
    cat = "Manual"
    if extra != "":
        extra = " " + extra
    d.update({'name': pvbase,
            'config' : 0,
            'owner' : hutch,
            'rec_base': pvbase,
            'category': cat,
            'mutex': '  ab',
            'comment': ioc + extra,
            'FLD_PORT': port,
            'FLD_DHLM': None,
            'FLD_DLLM': None })
    return d

def findMotors(cfglist, ioc):
    motors = []
    for (name, dir) in cfglist:
        if ioc != None and ioc != name:
            continue
        cfg = config()
        try:
            cfg.read_config(dir +  "/" + name + ".cfg", {})
        except:
            print("WARNING: %s has no configuration file!" % name)
            continue   # Wow, XCS has one *really* old controller!!
        for k in cfg.idict.keys():
            if k == 'MOTOR':
                for i in cfg.idict[k]:
                    motors.append(makeMotor(name, i['NAME'], i['PORT'], ""))
            elif k == 'IPM':
                for i in cfg.idict[k]:
                    motors.append(makeMotor(name, i['DIODE_X'], i['DDX_PORT'],
                                            i['NAME'] + " IPM DIODE_X"))
                    motors.append(makeMotor(name, i['DIODE_Y'], i['DDY_PORT'],
                                            i['NAME'] + " IPM DIODE_Y"))
                    motors.append(makeMotor(name, i['TARGET_Y'], i['TTY_PORT'],
                                            i['NAME'] + " IPM TARGET_Y"))
            elif k == 'PIM':
                for i in cfg.idict[k]:
                    motors.append(makeMotor(name, i['YAG'], i['PORT'],
                                            i['NAME'] + " PIM"))
            elif k == 'SLIT':
                for i in cfg.idict[k]:
                    motors.append(makeMotor(name, i['LEFT'], i['LEFT_PORT'],
                                            i['NAME'] + " SLIT LEFT"))
                    motors.append(makeMotor(name, i['RIGHT'], i['RIGHT_PORT'],
                                            i['NAME'] + " SLIT RIGHT"))
                    motors.append(makeMotor(name, i['TOP'], i['TOP_PORT'],
                                            i['NAME'] + " SLIT TOP"))
                    motors.append(makeMotor(name, i['BOTTOM'], i['BOTTOM_PORT'],
                                            i['NAME'] + " SLIT BOTTOM"))
            elif k == 'NAVITAR':
                for i in cfg.idict[k]:
                    motors.append(makeMotor(name, i['ZOOM'], i['ZOOM_PORT'],
                                            i['NAME'] + " ZOOM"))
                    try:
                        motors.append(makeMotor(name, i['FOCUS'], i['FOCUS_PORT'],
                                                i['NAME'] + " FOCUS"))
                    except:
                        pass
            elif k == 'XFLS':
                for i in cfg.idict[k]:
                    motors.append(makeMotor(name, i['X'], i['X_PORT'],
                                            i['NAME'] + " XFLS X"))
                    motors.append(makeMotor(name, i['Y'], i['Y_PORT'],
                                            i['NAME'] + " XFLS Y"))
                    try:
                        motors.append(makeMotor(name, i['Z'], i['Z_PORT'],
                                                i['NAME'] + " XFLS Z"))
                    except:
                        pass
            elif k == 'INOUT':
                for i in cfg.idict[k]:
                    motors.append(makeMotor(name, i['MOTOR'], i['PORT'],
                                            i['NAME'] + " INOUT"))
            elif k == 'REFL':
                for i in cfg.idict[k]:
                    motors.append(makeMotor(name, i['MIRROR'], i['PORT'],
                                            i['NAME'] + " REFL"))
    return motors

if __name__ == '__main__':
    # Options( [mandatory list, optional list, switches list] )
    options = Options(['hutch'], ['ioc'], ['debug'])
    try:
        options.parse()
    except Exception as msg:
        options.usage(str(msg))
        sys.exit()
    hutch   = options.hutch
    cfglist = readConfig()
    motors  = findMotors(cfglist, options.ioc)
    pmgr    = pmgrobj("ims_motor", hutch)
    if options.debug != None:
        for m in motors:
            print(m['name'], m['FLD_PORT'], caget(m['rec_base']+".PN"))
    else:
        pmgr.start_transaction()
        for m in motors:
            pmgr.objectInsert(m)
        errlist = pmgr.end_transaction()
        for e in errlist:
            print(e)
