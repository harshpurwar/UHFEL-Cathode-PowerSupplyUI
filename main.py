from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6 import uic
import sys
import pyvisa as pv

class MyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self = uic.loadUi('UIs/list.ui', self)
        self.errText.setVisible(False)

        self.refreshB.clicked.connect(self.refreshF)
        self.okB.clicked.connect(self.okF)

        self.rm = pv.ResourceManager()
        self.refreshF()

    def okF(self):
        it = self.deviceList.currentRow()
        if it != -1:
            print("Ok clicked. Selected row: {}".format(it))

    def refreshF(self):
        self.devices = self.rm.list_resources()
        if len(self.devices) == 0:
            self.errText.setVisible(True)
        else:
            self.errText.setVisible(False)
        self.deviceList.clear()
        self.deviceList.addItems(self.devices)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec())