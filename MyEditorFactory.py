from PyQt4 import QtCore, QtGui
import re
import numpy as np

# Code shamlessly stolen from http://jdreaver.com/posts/2014-07-28-scientific-notation-spin-box-pyside.html.
_float_re = re.compile(r'(([+-]?\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)')

def valid_float_string(string):
    match = _float_re.search(string)
    return match.groups()[0] == string if match else False

class FloatValidator(QtGui.QValidator):
    def validate(self, string, position):
        if valid_float_string(string):
            return (QtGui.QValidator.Acceptable, position)
        s = str(string)
        if s == "" or s[position-1] in 'e.-+':
            return (QtGui.QValidator.Intermediate, position)
        return (QtGui.QValidator.Invalid, position)

    def fixup(self, text):
        match = _float_re.search(str(text))
        return match.groups()[0] if match else ""

class ScientificDoubleSpinBox(QtGui.QDoubleSpinBox):
    def __init__(self, parent=None):
        QtGui.QDoubleSpinBox.__init__(self, parent)
        self.setMinimum(-np.inf)
        self.setMaximum(np.inf)
        self.validator = FloatValidator()
        self.setDecimals(1000)

    def validate(self, text, position):
        return self.validator.validate(text, position)

    def fixup(self, text):
        return self.validator.fixup(text)

    def valueFromText(self, text):
        return float(text)

    def textFromValue(self, value):
        return format_float(value)

    def stepBy(self, steps):
        text = self.cleanText()
        groups = _float_re.search(text).groups()
        decimal = float(groups[1])
        decimal += steps
        new_string = "{:g}".format(decimal) + (groups[3] if groups[3] else "")
        self.lineEdit().setText(new_string)


def format_float(value):
    """Modified form of the 'g' format specifier."""
    string = "{:g}".format(value).replace("e+", "e")
    string = re.sub("e(-?)0*(\d+)", r"e\1\2", string)
    return string

#
# MCB - If we define this, AND DON'T EVEN USE IT, we die with a segfault on exit.
#
class MyEditorFactory(QtGui.QItemEditorFactory):
    def __init__(self):
        QtGui.QItemEditorFactory.__init__(self)

    def createEditor(self, userType, parent):
        if userType != QtCore.QVariant.Double:
            return QtGui.QItemEditorFactory.createEditor(self, userType, parent)
        else:
            return ScientificDoubleSpinBox(parent)

    def valuePropertyName(self, userType):
        return QtGui.QItemEditorFactory.valuePropertyName(self, userType)
