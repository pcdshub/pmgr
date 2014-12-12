from PyQt4.QtGui import *
from PyQt4.QtCore import *

class MyDelegate(QStyledItemDelegate):
    def __init__(self, parent, cols, off):
        QStyledItemDelegate.__init__(self, parent)
        self.cols = cols
        self.off  = off

    def createEditor(self, parent, option, index):
        try:
            e = self.cols[index.column() - self.off]['enum']
            editor = QComboBox(parent)
            editor.enum = e
            editor.setAutoFillBackground(True)
            for item in e:
                editor.addItem(item)
            editor.mydelegate = True
        except:
            editor = QStyledItemDelegate.createEditor(self, parent, option, index)
            editor.mydelegate = False
        return editor

    def setEditorData(self, editor, index):
        if editor.mydelegate:
            value = index.model().data(index, Qt.EditRole).toString()
            idx = editor.enum.index(value)
            editor.setCurrentIndex(idx)
        else:
            QStyledItemDelegate.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        if editor.mydelegate:
            model.setData(index, QVariant(editor.currentText()))
        else:
            QStyledItemDelegate.setModelData(self, editor, model, index)

    def sizeHint(self, option, index):
        return QStyledItemDelegate.sizeHint(self, option, index)
