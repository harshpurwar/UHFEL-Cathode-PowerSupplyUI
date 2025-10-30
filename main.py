from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6 import uic
import sys,time
import pyvisa as pv
from PyQt6.QtCore import QTimer

class MainWindow(QWidget):
    def __init__(self, dev):
        super().__init__()
        self.inst = None
        # if dev == None:
            # self.close()
            # sys.exit(1)
        self.main = uic.loadUi('UIs/main.ui', self)
        self.main.led.setStyleSheet("color:red;")
        self.main.led.setText("\U00002B24")
        self.main.sVdB.setText("\U000002C5")
        self.main.sVuB.setText("\U000002C4")
        self.main.sCdB.setText("\U000002C5")
        self.main.sCuB.setText("\U000002C4")
        self.main.sVdB.clicked.connect(lambda x: self.stepUD(qty='VOLT', dir="DOWN"))
        self.main.sVuB.clicked.connect(lambda x: self.stepUD(qty='VOLT', dir="UP"))
        self.main.sCdB.clicked.connect(lambda x: self.stepUD(qty='CURR', dir="DOWN"))
        self.main.sCuB.clicked.connect(lambda x: self.stepUD(qty='CURR', dir="UP"))

        # self.rm = pv.ResourceManager()
        # self.inst = self.rm.open_resource(dev)
        # self.title.setText(self.inst.query("*IDN?").strip())
        # self.main.sVoltage.display(self.inst.query("VOLT?"))
        # self.main.sCurrent.display(self.inst.query("CURR?"))
        # self.main.mVoltage.display(self.inst.query("MEAS:VOLT?"))
        # self.main.mCurrent.display(self.inst.query("MEAS:CURR?"))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000) # auto update time in ms
        
        self.main.led.setStyleSheet("color:green;")
        self.main.show()

    def stepUD(self,qty,dir):
        if qty == "VOLT":
            if self.main.sVCoarse.value() == 0:
                step=0.1
            else:
                step=1
        elif qty=="CURR":
            if self.main.sCCoarse.value() == 0:
                step=0.1
            else:
                step=1
        print("Stepping {} {}".format(qty,dir))
        # self.inst.write("{}:STEP {}".format(qty,step))
        # self.inst.write("{} {}".format(qty,dir))
        


    def update(self):
        self.main.led.setStyleSheet("color:red;")
        # self.main.mVoltage.display(self.inst.query("MEAS:VOLT?"))
        # self.main.mCurrent.display(self.inst.query("MEAS:CURR?"))
        self.main.led.setStyleSheet("color:green;")

    def close(self):
        if not self.inst == None:
            self.inst.close()
        super().close()
        



class DevWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.devWin = uic.loadUi('UIs/devWin.ui', self)
        self.devWin.errText.setVisible(False)
        # self.devWin.okB.setDisabled(True)

        self.devWin.refreshB.clicked.connect(self.refreshF)
        self.devWin.okB.clicked.connect(self.okF)

        self.rm = pv.ResourceManager()
        self.refreshF()

    def okF(self):
        if self.deviceList.currentRow() != -1:
            selectedDevice = self.deviceList.currentItem().text()
        else:
            selectedDevice = None
        self.devWin.close()
        self.main = MainWindow(selectedDevice)
        self.main.show()

    def refreshF(self):
        self.devices=dict()
        keys = self.rm.list_resources()
        if len(keys) == 0:
            self.devWin.errText.setVisible(True)
        else:
            self.devWin.okB.setDisabled(False)
            self.devWin.errText.setVisible(False)
            for i,key in enumerate(keys):
                inst = self.rm.open_resource(key)
                idn = inst.query('*IDN?')
                inst.close()
                self.devices[key] = key + " --> " + idn.strip()

        self.devWin.deviceList.clear()
        self.devWin.deviceList.addItems(self.devices.values())
        self.devWin.deviceList.setCurrentRow(0)
        self.devWin.status.setPlainText("Refreshing... Done!")
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DevWindow()
    window.show()
    sys.exit(app.exec())