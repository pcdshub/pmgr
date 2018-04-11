from PyQt5 import QtCore, QtGui, QtWidgets

######################################################################

class FreezeHeaderView(QtWidgets.QHeaderView):
    def __init__(self, orientation, parent=None):
        QtWidgets.QHeaderView.__init__(self, orientation, parent)
        self.__hdr = None
        self.__parent = parent
        self.__orientation = orientation
        self.sortindicator = (None, None)
        self.sectionResized.connect(self.updateSectionWidth)
        self.sortIndicatorChanged.connect(self.selfSortChanged)
        #MCB self.setClickable(True)  # Sigh.  Why isn't this done when we ask it to be sortable?!?

    def setShadowHeader(self, hdr):
        self.__hdr = hdr
        self.__hdr.sortIndicatorChanged.connect(self.parentSortChanged)

    def sectionSizeFromContents(self, logidx):
        if self.__hdr == None:
            return QtWidgets.QHeaderView.sectionSizeFromContents(self, logidx)
        elif self.__orientation == QtCore.Qt.Horizontal:
            return QtCore.QSize(self.__hdr.sectionSize(logidx), self.__hdr.height())
        else:
            return QtCore.QSize(self.__hdr.width(), self.__hdr.sectionSize(logidx))

    def updateSectionWidth(self, logidx, oldsize, newsize):
        if self.__hdr.sectionSize(logidx) == oldsize and newsize != 0:
            self.__hdr.resizeSection(logidx, newsize)

    def selfSortChanged(self, logidx, order):
        if (logidx, order) != self.sortindicator:
            self.sortindicator = (logidx, order)
            self.__hdr.setSortIndicator(logidx, order)

    def parentSortChanged(self, logidx, order):
        if (logidx, order) != self.sortindicator:
            self.sortindicator = (logidx, order)
            self.setSortIndicator(logidx, order)

######################################################################

class DropTableView(QtWidgets.QTableView):
    def __init__(self, parent, rows, cols, name):
        QtWidgets.QTableView.__init__(self, parent)
        self.hiderows = rows
        self.hidecols = cols
        self.debugname = name
        self.menus = []
        self.hmenus = []
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.horizontalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # MCB - This doesn't work.  Probably because we aren't actually
        # tracking the selection, just clearing it when it isn't visible.
        # So just turn it off.
        self.horizontalHeader().setHighlightSections(False)
        
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.showHeaderContextMenu)

    #
    # We're cheating here.  We are making a distinction between a drag (which
    # becomes a CopyAction) and a shift-drag (which becomes a MoveAction).
    # However, we don't really want to ever move, since that automatically
    # deletes the source data in the model.  Therefore, in our dropEvent,
    # we remember what we wanted, but force everything to be CopyAction.
    #
    def dropEvent(self, event):
        self.model().originalAction = event.proposedAction()
        if event.proposedAction() == QtCore.Qt.MoveAction:
            event.setDropAction(QtCore.Qt.CopyAction)
        QtWidgets.QTableView.dropEvent(self, event)

    def setModel(self, model):
        QtWidgets.QTableView.setModel(self, model)
        model.columnsInserted.connect(self.insertColumns)
        model.rowsInserted.connect(self.insertRows)
        
    def insertColumns(self, parent, start, finish):
        if self.hidecols != -1:
            if self.model().columnCount() != self.horizontalHeader().count():
                # Sigh.  We have a race condition.  Just reschedule for later.
                QtCore.QTimer.singleShot(0, lambda : self.hideAllColumns(start))
            else:
                for col in range(start, finish+1):
                    if col >= self.hidecols:
                        self.setColumnHidden(col, True)
    
    def insertRows(self, parent, start, finish):
        if self.hiderows != -1:
            if self.model().rowCount() != self.verticalHeader().count():
                # Sigh.  We have a race condition.  Just reschedule for later.
                QtCore.QTimer.singleShot(0, lambda : self.hideAllRows(start))
            else:
                for row in range(start, finish+1):
                    if row >= self.hiderows:
                        self.setRowHidden(row, True)

    def hideAllColumns(self, start):
        if self.model().columnCount() != self.horizontalHeader().count():
            # Still racing!
            QtCore.QTimer.singleShot(0, lambda : self.hideAllColumns(start))
        else:
            for col in range(start, self.model().columnCount()):
                if col >= self.hidecols:
                    self.setColumnHidden(col, True)

    def hideAllRows(self, start):
        if self.model().rowCount() != self.verticalHeader().count():
            # Still racing!
            QtCore.QTimer.singleShot(0, lambda : self.hideAllRows(start))
        else:
            for row in range(start, self.model().rowCount()):
                if row >= self.hiderows:
                    self.setRowHidden(row, True)

    def addContextMenu(self, menu):
        self.menus.append(menu)

    def addHeaderContextMenu(self, menu):
        self.hmenus.append(menu)

    #
    # Look through the list of context menus to find one that applies
    # at the current location.
    #
    def showContextMenu(self, pos):
        index = self.indexAt(pos)
        for m in self.menus:
            if m.isActive(self, index):
                m.doMenu(self, pos, index)
                return

    def showHeaderContextMenu(self, pos):
        index = self.horizontalHeader().logicalIndexAt(pos)
        for m in self.hmenus:
            if m.isActive(self, index):
                m.doMenu(self, pos, index)
                return

######################################################################
    
class FreezeTableView(DropTableView):
    def __init__(self, parent=None):
        DropTableView.__init__(self, parent, -1, -1, "main")
        self.didinit = False

    def init(self, model, rows=0, cols=0):
        self.setModel(model)
        self.frows = rows
        self.fcols = cols
        self.frowheight = 0
        self.fcolwidth = 0
        self.setStyleSheet("QTableView { border: none; }")

        fTV = DropTableView(self, self.frows, self.fcols, "fTV")
        self.fTV = fTV
        fTV.setModel(self.model())
        fTV.setHorizontalHeader(FreezeHeaderView(QtCore.Qt.Horizontal, self))
        fTV.horizontalHeader().setShadowHeader(self.horizontalHeader())
        fTV.setVerticalHeader(FreezeHeaderView(QtCore.Qt.Vertical, self))
        fTV.verticalHeader().setShadowHeader(self.verticalHeader())
        fTV.setStyleSheet("QTableView { border: none; }")
        #fTV.setStyleSheet("QTableView { border: none; background-color: #FF0000  }")
        #fTV.horizontalHeader().setStyleSheet("QHeaderView { background-color: #FF0000  }")

        for col in range(self.model().columnCount()):
            if col >= self.fcols:
                fTV.setColumnHidden(col, True)
        for row in range(self.model().rowCount()):
            if row >= self.frows:
                fTV.setRowHidden(row, True)
        fTV.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        fTV.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    
        cTV = DropTableView(self, -1, self.fcols, "cTV")
        self.cTV = cTV
        cTV.setModel(self.model())
        cTV.verticalHeader().hide()
        cTV.horizontalHeader().hide()
        cTV.setStyleSheet("QTableView { border: none; }")
        for col in range(self.model().columnCount()):
            if col >= self.fcols:
                cTV.setColumnHidden(col, True)
        for row in range(self.frows):
            cTV.setRowHidden(row, True)
        cTV.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        cTV.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        rTV = DropTableView(self, self.frows, -1, "rTV")
        self.rTV = rTV

        rTV.setModel(self.model())
        rTV.verticalHeader().hide()
        rTV.horizontalHeader().hide()
        rTV.setStyleSheet("QTableView { border: none; }")

        for col in range(self.fcols):
            rTV.setColumnHidden(col, True)
        for row in range(self.model().rowCount()):
            if row >= self.frows:
                rTV.setRowHidden(row, True)
        rTV.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        rTV.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.verticalHeader().setDefaultSectionSize(25)
        cTV.verticalHeader().setDefaultSectionSize(25)
        fTV.verticalHeader().setDefaultSectionSize(25)
        rTV.verticalHeader().setDefaultSectionSize(25)

        self.horizontalHeader().setDefaultSectionSize(25)
        cTV.horizontalHeader().setDefaultSectionSize(25)
        fTV.horizontalHeader().setDefaultSectionSize(25)
        rTV.horizontalHeader().setDefaultSectionSize(25)

        # Order from top: fTV, cTV, rTV, viewport
        self.viewport().stackUnder(rTV)
        self.viewport().stackUnder(cTV)
        self.viewport().stackUnder(fTV)

        rTV.stackUnder(cTV)
        rTV.stackUnder(fTV)

        cTV.stackUnder(fTV)

        fTV.show()
        cTV.show()
        rTV.show()

        self.updateFTGeometry()

        self.setHorizontalScrollMode(self.ScrollPerPixel)
        self.setVerticalScrollMode(self.ScrollPerPixel)
        cTV.setVerticalScrollMode(self.ScrollPerPixel)
        rTV.setHorizontalScrollMode(self.ScrollPerPixel)

        self.setFrozenColWidth()
        self.setFrozenRowHeight()

        # Share a delegate!
        delegate = self.itemDelegate()
        self.fTV.setItemDelegate(delegate)
        self.cTV.setItemDelegate(delegate)
        self.rTV.setItemDelegate(delegate)
        
        self.horizontalHeader().sectionResized.connect(self.updateSectionWidth)
        self.verticalHeader().sectionResized.connect(self.updateSectionHeight)
        
        cTV.verticalScrollBar().valueChanged.connect(self.verticalScrollBar().setValue)
        self.verticalScrollBar().valueChanged.connect(cTV.verticalScrollBar().setValue)
        
        rTV.horizontalScrollBar().valueChanged.connect(self.horizontalScrollBar().setValue)
        self.horizontalScrollBar().valueChanged.connect(rTV.horizontalScrollBar().setValue)

        self.selectionModel().selectionChanged.connect(self.parentSelectionChanged)
        cTV.selectionModel().selectionChanged.connect(self.colSelectionChanged)
        rTV.selectionModel().selectionChanged.connect(self.rowSelectionChanged)
        fTV.selectionModel().selectionChanged.connect(self.frozenSelectionChanged)

        self.horizontalHeader().sectionMoved.connect(self.fixColumnMove)
        self.didinit = True

    #
    # OK, too clever by half.  We had a problem, when sharing a selection model,
    # if the selected column was hidden in the child, all of the columns would
    # suddenly become visible.  So now we're just using separate models, and
    # trying to keep them in sync.  Easier than one would think, as the first column
    # can only be selected in the child, and the detectors (the first row after the
    # parameter headers) can only be selected in the parent.  So when we get a selection,
    # clear the other guy!
    #
    def parentSelectionChanged(self, selected, deselected):
        if not selected.isEmpty():
            self.cTV.selectionModel().clear()
            self.rTV.selectionModel().clear()
            self.fTV.selectionModel().clear()

    def colSelectionChanged(self, selected, deselected):
        if not selected.isEmpty():
            self.selectionModel().clear()
            self.rTV.selectionModel().clear()
            self.fTV.selectionModel().clear()

    def rowSelectionChanged(self, selected, deselected):
        if not selected.isEmpty():
            self.selectionModel().clear()
            self.cTV.selectionModel().clear()
            self.fTV.selectionModel().clear()

    def frozenSelectionChanged(self, selected, deselected):
        if not selected.isEmpty():
            self.selectionModel().clear()
            self.cTV.selectionModel().clear()
            self.rTV.selectionModel().clear()

    def clearSelection(self):
        self.selectionModel().clear()
        self.cTV.selectionModel().clear()
        self.rTV.selectionModel().clear()
        self.fTV.selectionModel().clear()

    def setRowHidden(self, row, hide):
        DropTableView.setRowHidden(self, row, hide)
        self.cTV.setRowHidden(row, hide)
        if row < self.frows:
            self.fTV.setRowHidden(row, hide)
        else:
            self.rTV.setRowHidden(row, hide)

    def setSortingEnabled(self, value):
        DropTableView.setSortingEnabled(self, value)
        self.cTV.setSortingEnabled(value)
        self.rTV.setSortingEnabled(value)
        self.fTV.setSortingEnabled(value)
        
    def addHorizontalSectionWidget(self, logidx, w):
        self.itemDelegate().addSectionWidget(logidx, w, self)

    def setFrozenColWidth(self):
        total = 0
        for i in range(self.fcols):
            total += self.columnWidth(i)
        self.fcolwidth = total

    def setFrozenRowHeight(self):
        total = 0
        for i in range(self.frows):
            total += self.rowHeight(i)
        self.frowheight = total

    def updateSectionWidth(self, idx, oldSize, newSize):
        self.rTV.setColumnWidth(idx, newSize)
        self.fTV.setColumnWidth(idx, newSize)
        self.cTV.setColumnWidth(idx, newSize)
        if idx < self.fcols:
            self.setFrozenColWidth()
        self.updateFTGeometry()

    def updateSectionHeight(self, idx, oldSize, newSize):
        self.cTV.setRowHeight(idx, newSize)
        self.fTV.setRowHeight(idx, newSize)
        self.rTV.setRowHeight(idx, newSize)
        if idx < self.frows:
            self.setFrozenRowHeight()
        self.updateFTGeometry()

    def resizeEvent(self, event):
        DropTableView.resizeEvent(self, event)
        if self.didinit:
            self.updateFTGeometry()

    def moveCursor(self, ca, mods):
        cur = DropTableView.moveCursor(self, ca, mods)
        if (ca == QtWidgets.QAbstractItemView.MoveLeft and cur.column() > 0 and
            self.visualRect(cur).topLeft().x() < self.fcolwidth):
            nv = (self.horizontalScrollBar().value() + self.visualRect(cur).topLeft().x() -
                  self.fcolwidth)
            self.horizontalScrollBar().setValue(nv)
        if (ca == QtWidgets.QAbstractItemView.MoveUp and cur.row() > 0 and
            self.visualRect(cur).topLeft().y() < self.frowheight):
            nv = (self.verticalScrollBar().value() + self.visualRect(cur).topLeft().y() -
                  self.frowheight)
            self.verticalScrollBar().setValue(nv)
        return cur

    def scrollTo(self, index, hint):
        if index.column() > 0:
            DropTableView.scrollTo(self, index, hint)

    def updateFTGeometry(self):
        self.fTV.setGeometry((self.frameWidth() +
                              (self.verticalHeader().width() if self.frowheight == 0 else 0)),
                             (self.frameWidth() +
                              (self.horizontalHeader().height() if self.fcolwidth == 0 else 0)),
                             (self.fcolwidth + (self.verticalHeader().width()
                                               if self.frowheight != 0 else 0)),
                             (self.frowheight + (self.horizontalHeader().height()
                                                 if self.fcolwidth != 0 else 0)))
        self.cTV.setGeometry(self.verticalHeader().width() + self.frameWidth(),
                             self.horizontalHeader().height() + self.frameWidth() + self.frowheight,
                             self.fcolwidth,
                             self.viewport().height() - self.frowheight)
        self.rTV.setGeometry(self.verticalHeader().width() + self.frameWidth() + self.fcolwidth,
                             self.horizontalHeader().height() + self.frameWidth(),
                             self.viewport().width() - self.fcolwidth,
                             self.frowheight)

    def setHorizontalHeader(self, header):
        DropTableView.setHorizontalHeader(self, header)
        self.fTV.horizontalHeader().setShadowHeader(self.horizontalHeader())
        self.horizontalHeader().sectionResized.connect(self.updateSectionWidth)
        
    def setItemDelegateForRow(self, row, delegate):
        DropTableView.setItemDelegateForRow(self, row, delegate)
        self.fTV.setItemDelegateForRow(row, delegate)
        self.cTV.setItemDelegateForRow(row, delegate)
        self.rTV.setItemDelegateForRow(row, delegate)
        
    def setItemDelegateForColumn(self, column, delegate):
        DropTableView.setItemDelegateForColumn(self, column, delegate)
        self.fTV.setItemDelegateForColumn(column, delegate)
        self.cTV.setItemDelegateForColumn(column, delegate)
        self.rTV.setItemDelegateForColumn(column, delegate)
        
    def setItemDelegate(self, delegate):
        DropTableView.setItemDelegate(self, delegate)
        self.fTV.setItemDelegate(delegate)
        self.cTV.setItemDelegate(delegate)
        self.rTV.setItemDelegate(delegate)

    def openPersistentEditor(self, index):
        if index.row() < self.frows:
            if index.column() < self.fcols:
                self.fTV.openPersistentEditor(index)
            else:
                self.rTV.openPersistentEditor(index)
        else:
            if index.column() < self.fcols:
                self.cTV.openPersistentEditor(index)
            else:
                DropTableView.openPersistentEditor(self, index)

    def setEditTriggers(self, triggers):
        DropTableView.setEditTriggers(self, triggers)
        self.fTV.setEditTriggers(triggers)
        self.cTV.setEditTriggers(triggers)
        self.rTV.setEditTriggers(triggers)

    def setShowGrid(self, state):
        DropTableView.setShowGrid(self, state)
        self.fTV.setShowGrid(state)
        self.cTV.setShowGrid(state)
        self.rTV.setShowGrid(state)

    def setColumnWidth(self, col, size):
        DropTableView.setColumnWidth(self, col, size)
        self.fTV.setColumnWidth(col, size)
        self.cTV.setColumnWidth(col, size)
        self.rTV.setColumnWidth(col, size)

    def setRowHeight(self, row, size):
        DropTableView.setRowHeight(self, row, size)
        self.fTV.setRowHeight(row, size)
        self.cTV.setRowHeight(row, size)
        self.rTV.setRowHeight(row, size)

    def printSize(self, n):
        print("%d: main=%d, fTV=%d, rTV=%d, cTV=%d" % (n, self.rowHeight(n), self.fTV.rowHeight(n),
                                                       self.rTV.rowHeight(n), self.cTV.rowHeight(n)))

    def addContextMenu(self, menu):
        DropTableView.addContextMenu(self, menu)
        self.cTV.addContextMenu(menu)
        self.rTV.addContextMenu(menu)
        self.fTV.addContextMenu(menu)

    def fixColumnMove(self, logidx, oldvis, newvis):
        self.rTV.horizontalHeader().moveSection(oldvis, newvis)
        # If a frozen column tries to move, move it right back!
        if newvis < self.fcols:
            self.horizontalHeader().moveSection(newvis, oldvis)

    def restoreHeaderState(self, data):
        self.horizontalHeader().restoreState(data)
        self.fTV.horizontalHeader().restoreState(data)
        self.rTV.horizontalHeader().restoreState(data)
        self.cTV.horizontalHeader().restoreState(data)
        for col in range(self.model().columnCount()):
            if col >= self.fcols:
                self.fTV.setColumnHidden(col, True)
                self.cTV.setColumnHidden(col, True)
            else:
                self.rTV.setColumnHidden(col, True)

    def saveHeaderState(self):
        return self.horizontalHeader().saveState()

    def showColumn(self, c):
        self.rTV.horizontalHeader().showSection(c)
        DropTableView.showColumn(self, c)

    def resizeColumnsToContents(self):
        DropTableView.resizeColumnsToContents(self)
        self.restoreHeaderState(self.saveHeaderState())
