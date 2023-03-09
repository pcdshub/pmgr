# Parameter Manager

Package used in LCLS to manage motor parameters. Currently in use to manage
configurations for IMS motors in the LCLS1 hard x-ray hutches.

## Implementation Notes

```
We assume that there are a number of "classes" of things to be configured.
If one such class is XXX, then we will have three mysql tables for it:
    -- XXX_cfg is a table of configurations.
    -- XXX_name_map is a table of field aliases.
    -- XXX is a table of configured objects.

The first set of fields in each of these tables is fixed, so we can operate
generically on any configuration class.

The configurations in XXX_cfg start with the following fields:
  `id` int(11) NOT NULL AUTO_INCREMENT,          -- The primary key
  `name` varchar(15) NOT NULL UNIQUE,            -- The name of the configuration
  `config` int(11),                              -- The parent configuration
  `security` varchar(30),
  `owner` varchar(10),
  `dt_updated` datetime NOT NULL,
  `mutex` varchar(16),

It is assumed that there will always be a "DEFAULT" configuration with id 0.  This will
be the only configuration with a null link.  This should be a "no-op" configuration!

After these, there will be many fields of various types all named "FLD_*" or
"PV_*". The idea is that each configuration will be applied to a base PV name.
 The "_*" is what should be appended to the base PV name.  Any "__" will be
changed to a single "_" in the actual name, and any single "_" will be changed
to ":" with the exception of the last.  For "FLD", the last "_" will become "."
while for "PV" it will become "_".

For example if the base is IOC:TST:01:CTRL,
	FLD_XY       -> IOC:TST:01:CTRL.XY
	PV_XY        -> IOC:TST:01:CTRL:XY
	FLD_XY_Z     -> IOC:TST:01:CTRL:XY.Z
	PV_XY_Z      -> IOC:TST:01:CTRL:XY:Z
	FLD_XY__Z    -> IOC:TST:01:CTRL.XY_Z
	PV_XY__Z     -> IOC:TST:01:CTRL:XY_Z

This is implemented by the function fixName.

The XXX_name_map table has fields:
  `db_field_name` varchar(30) NOT NULL,      -- The FLD_* or PV_* field name.
  `alias` varchar(16) NOT NULL,              -- A human-readable alias for this field.
  `tooltip` varchar(60),                     -- A tooltip for the field.
  `enum` varchar(120),                       -- If an enum type, possible names, separated by '|'.
  `col_order` int(11) UNIQUE,                -- Where this field should be displayed (< = more left).
  `set_order` int(11),                       -- How to set this field.  Low ten-bits are order (< = set earlier)
					     -- 0x0200 flags this as a mutex group.
					     -- 0x0400 flags a must-write PV.
					     -- 0x0800 flags a write zero, then write value PV.
					     -- 0x1000 flags the "autoconfiguration" PV (deprecated!!!).
					     -- 0x2000 flags a read-only value.
  `mutex_mask` int(10) unsigned              -- A bitmask of values that are interrelated.  Each bit is a different set,
                                             -- so a field can be in several sets.

The XXX table has fields:
  `id` int(11) NOT NULL AUTO_INCREMENT,      -- The identifier of this object.
  `config` int(11) NOT NULL,                 -- The configuration id of this object.
  `owner` varchar(10),	                     -- Which hutch owns this object.
  `name` varchar(30) NOT NULL,               -- The name of this object.
  `category` varchar(10),
  `rec_base` varchar(40) NOT NULL,           -- pv/field base prefix --
  `mutex` varchar(16),
  `dt_created` datetime NOT NULL,            -- When the record was created.
  `dt_updated` datetime NOT NULL,            -- When the record was modified.
  `comment`  varchar(80),

After these fields, the XXX table may also have "FLD_*" and "PV_*" fields
as described above.  (These should be object specific things that are always
unique to the object, such as descriptions and digi port addresses.)

mutex is magic in both XXX and XXX_cfg. There is one character for each mutex set,
indicating the unset (derived) value in this set.  The coding is 0x40 + colorder,
where each field must have a unique colorder value.
```

### IMS Motor

```
The weirdness for IMS motors is that we have some derived values:
	ERES = UREV / (4 * EL)
	MRES = UREV / (FREV * MS)

Now, FREV and MS are not really changeable (they are hardware parameters),
so we can solve the latter by saying that [MRES, UREV] is a mutual exclusion
set.

The situation is a little weirder for the first equation.
    - If you set UREV, ERES changes.
    - If you set ERES or EL, the other one changes.

So, we solve this by calling [ERES, EL] a mutual exclusion set, and ordering
writes:
    - UREV is first (setorder 1).
    - ERES and EL are later (setorder 2).
    - ERES is also "must write" (setorder is negative!).

So if we want EL to be the derived value:
    - We write UREV (which changes ERES).
    - We write ERES (which changes EL).

```

### Name map table

```
The *_name_map table has the following fields:
	db_field_name - The name of the field, used to access the PV.  It either
	                starts "FLD_" (indicating that the name is to be appended
			to the base name with a period) or "PV_" (indicating that
			the name is to be appended to the base name with a colon.)
			Double underscores are converted to single throughout.
	alias         - The short name of the field, put into the column header.
	tooltip	      - The tooltip for the field.
        enum          - If the PV is an enum, the possible values are listed here,
			separated by |.  (If this isn't an empty string, the editor
		        will be a QComboBox with the listed values.)
        col_order     - A unique identifier for the field which also gives the
			default column order (low numbers first).
	set_order     - A field giving PV setting information.  This has several
			bitfields:
			    - The low 10 bits are the order.  Order 0 is written
			      first, then order 1, etc.
			    - 0x200 flags this order as a mutex group as well.
			      Fields in a mutex group must have distinct non-zero
                              values.
			    - 0x400 flags a PV that must be written, even if the
			      value doesn't seem to change.
			    - 0x800 flags a PV that must be set to zero first.
			    - 0x1000 flags the "autoconfiguration" PV (the serial
			      number).
			    - 0x2000 flags "readonly" PVs.
	mutex_mask    - If several values are interrelated, this value will be
			non-zero.  It is a bitmask of values in the interrelated
			set.  Several bits can be 1 if this field is in several
			sets.
```

### Logging into MySQL

```
Log into MySQL with the following commands:

Server is psdb.slac.stanford.edu, though you can log in from
psdev because of the --host=psdb argument...


(ADMIN MODE)

> mysql --host=psdb --user=pscontrolsa --password=pcds pscontrols


(USER MODE)

> mysql --host=psdb --user=pscontrols --password=pcds pscontrols
```
