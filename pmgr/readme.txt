Log into MySQL with the following commands:

Server is psdb.slac.stanford.edu, though you can log in from
psdev because of the --host=psdb argument...


(ADMIN MODE)

> mysql --host=psdb --user=pscontrolsa --password=pcds pscontrols


(USER MODE)

> mysql --host=psdb --user=pscontrols --password=pcds pscontrols

