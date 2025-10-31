from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6 import uic
import sys,time
import pyvisa as pv
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

class Worker(QThread):
    finished = pyqtSignal()
    
    def setData(self,data,inst,qty,dt):
        self.data=data
        self.inst = inst
        self.qty=qty
        self.dt=dt

    def run(self):
        for i in self.data:
            self.inst.write("{} {}".format(self.qty,i))
            time.sleep(self.dt)
        self.finished.emit()

class MainWindow(QWidget):
    def __init__(self, dev):
        super().__init__()

        if dev == None:
            self.inst = None
            self.close()
            sys.exit(1)

        self.main = uic.loadUi('UIs/main.ui', self)
        self.main.sVdB.setText("\U000002C5")
        self.main.sVuB.setText("\U000002C4")
        self.main.sCdB.setText("\U000002C5")
        self.main.sCuB.setText("\U000002C4")
        self.main.refreshB.setText("\U000021BB")
        self.main.sVdB.clicked.connect(lambda x: self.stepUD(qty='VOLT', dir="DOWN"))
        self.main.sVuB.clicked.connect(lambda x: self.stepUD(qty='VOLT', dir="UP"))
        self.main.sCdB.clicked.connect(lambda x: self.stepUD(qty='CURR', dir="DOWN"))
        self.main.sCuB.clicked.connect(lambda x: self.stepUD(qty='CURR', dir="UP"))
        self.main.outB.clicked.connect(self.outF)
        self.main.sVRampB.clicked.connect(lambda x: self.rampF(qty='VOLT'))
        self.main.sCRampB.clicked.connect(lambda x: self.rampF(qty='CURR'))
        self.main.refreshB.clicked.connect(self.refreshF)

        self.rm = pv.ResourceManager()
        self.inst = self.rm.open_resource(dev)

        self.refreshF()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000) # auto update time in ms
        
        self.worker = Worker()
        self.worker.finished.connect(self.onRampCompletion)
    
    def onRampCompletion(self):
        self.main.rampB.setEnabled(True)

    def refreshF(self):
        val = self.inst.query("*IDN?").strip().split(',')
        self.title.setText("{} - {}".format(val[0],val[1]))
        b = val[2].split('/')
        self.subTitle.setText("Part#: {}, Serial#: {}, FW ver.: {}".format(b[0],b[1],val[3]))
        self.main.sVoltage.setText('{:.3f}'.format(float(self.inst.query("VOLT?").strip())))
        self.main.sCurrent.setText('{:.3f}'.format(float(self.inst.query("CURR?").strip())))
        if int(self.inst.query("OUTP:STAT?")) == 1:
            self.main.outB.setStyleSheet("background-color: #00F000;")
        else:
            self.main.outB.setStyleSheet("background-color: #000F00;")

    def rampF(self,qty):
        self.main.rampB.setEnabled(False)
        c = float(self.inst.query("{}?".format(qty)).strip())
        if qty == "VOLT":
            s = float(self.main.sVoltage.text().strip())
            if s>32: 
                s=32.0
            n = int(self.main.sVN.text().strip())
            dt = float(self.main.sVdt.text().strip())
        else:
            s = float(self.main.sCurrent.text().strip())
            if s>10:
                s=10.0
            n = int(self.main.sCN.text().strip())
            dt = float(self.main.sCdt.text().strip())
        vals = np.linspace(c,s,n)
        self.worker.setData(vals, self.inst, qty, dt)
        self.worker.start()

    def outF(self):
        val = int(self.inst.query("OUTP:STAT?"))
        self.inst.write("OUTP:STAT {}".format(1-val))
        if val == 1:
            self.main.outB.setStyleSheet("background-color: #000F00;")
        else:
            self.main.outB.setStyleSheet("background-color: #00F000;")

    def stepUD(self,qty,dir):
        if qty == "VOLT":
            if self.main.sVCoarse.value() == 0:
                step = 0.01
            elif self.main.sVCoarse.value() == 1:
                step = 0.1
            else:
                step=1
            if dir == "UP":
                self.main.sVoltage.setText('{:.3f}'.format(float(self.main.sVoltage.text())+step))
            else:
                self.main.sVoltage.setText('{:.3f}'.format(float(self.main.sVoltage.text())-step))
        elif qty=="CURR":
            if self.main.sCCoarse.value() == 0:
                step=0.01
            elif self.main.sCCoarse.value() == 1:
                step=0.1
            else:
                step=1
            if dir == "UP":
                self.main.sCurrent.setText('{:.3f}'.format(float(self.main.sCurrent.text())+step))
            else:
                self.main.sCurrent.setText('{:.3f}'.format(float(self.main.sCurrent.text())-step))        
        self.inst.write("{}:STEP {}".format(qty,step))
        self.inst.write("{} {}".format(qty,dir))
        
    def update(self):
        self.main.mVoltage.display(self.inst.query("MEAS:VOLT?").strip())
        self.main.mCurrent.display(self.inst.query("MEAS:CURR?").strip())
        self.main.power.setText("Power: {:.3f}".format(float(self.inst.query("MEAS:POW?").strip())))

    def close(self):
        if not self.inst == None:
            self.inst.close()
        super().close()
        



class DevWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.devWin = uic.loadUi('UIs/devWin.ui', self)
        self.devWin.errText.setVisible(False)
        self.devWin.okB.setDisabled(True)

        self.devWin.refreshB.clicked.connect(self.refreshF)
        self.devWin.okB.clicked.connect(self.okF)

        self.rm = pv.ResourceManager()
        self.refreshF()

    def okF(self):
        if self.deviceList.currentRow() != -1:
            selectedDevice = self.deviceList.currentItem().text().split(' --> ')[0]
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
                try:
                    inst = self.rm.open_resource(key)
                    idn = inst.query('*IDN?').strip()
                    inst.close()
                except:
                    idn='Unknown'
                self.devices[key] = key + " --> " + idn

        self.devWin.deviceList.clear()
        self.devWin.deviceList.addItems(self.devices.values())
        self.devWin.deviceList.setCurrentRow(0)
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DevWindow()
    window.show()
    sys.exit(app.exec())