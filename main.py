from PyQt6.QtWidgets import QApplication, QWidget, QSizePolicy
from PyQt6 import uic
import sys,time
import pyvisa as pv
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from datetime import datetime
from random import randint

# Add logging - Start and Stop logging buttons

offline=True
lock=False

class Worker(QThread):
    finished = pyqtSignal(str)
    
    def setData(self,obj,data,qty,dt):
        self.data=data
        self.mainThread = obj
        self.qty=qty
        self.dt=dt

    def run(self):
        for i in self.data:
            self.mainThread.myWrite("{} {}".format(self.qty,i))
            time.sleep(self.dt)
        self.finished.emit(self.qty)

class MainWindow(QWidget):

    X = []
    Y1 = []; Y2 = []

    def __init__(self, dev):
        super().__init__()

        if not offline and dev == None:
            self.inst = None
            self.close()
            sys.exit(1)
        else:
            self.dev = dev

        heve = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.main = uic.loadUi('UIs/main.ui', self)
        self.main.setWindowState(self.main.windowState() | Qt.WindowState.WindowMaximized)
        if offline:
            self.main.setWindowTitle(self.main.windowTitle()+' (Offline)')
        self.main.sVdB.setText("\U000002C5")
        self.main.sVuB.setText("\U000002C4")
        self.main.sCdB.setText("\U000002C5")
        self.main.sCuB.setText("\U000002C4")
        self.main.sVdB.clicked.connect(lambda x: self.stepUD(qty='VOLT', dir="DOWN"))
        self.main.sVuB.clicked.connect(lambda x: self.stepUD(qty='VOLT', dir="UP"))
        self.main.sCdB.clicked.connect(lambda x: self.stepUD(qty='CURR', dir="DOWN"))
        self.main.sCuB.clicked.connect(lambda x: self.stepUD(qty='CURR', dir="UP"))
        self.main.outB.clicked.connect(self.outF)
        self.main.sVRampB.clicked.connect(lambda x: self.rampF(qty='VOLT'))
        self.main.sCRampB.clicked.connect(lambda x: self.rampF(qty='CURR'))
        self.main.refreshB.clicked.connect(self.refreshF)

        if not offline:
            self.rm = pv.ResourceManager()
            self.inst = self.rm.open_resource(dev)
        else:
            self.rm = None
            self.inst = None

        self.refreshF()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        # self.timer.start(100) # auto update time in ms

        self.fig = Figure(); 
        self.ax1 = self.fig.add_subplot(); self.ax2 = self.ax1.twinx()
        self.drawPlot()

        self.main.canvas = FigureCanvasQTAgg(self.fig)
        self.main.canvas.setSizePolicy(heve)
        self.main.layout().addWidget(self.main.canvas,14,0,1,8)
        
        self.timer2 = QTimer(self)
        self.timer2.timeout.connect(self.updatePlot)
        # self.timer2.start(1000) # auto update time in ms

        self.worker = Worker()
        self.worker.finished.connect(self.onRampCompletion)

    def myQuery(self,cmd):
        global lock
        while lock:
            time.sleep(10e-6)
        lock=True
        if not offline:
            r = self.inst.query(cmd).strip()
        else:
            r='0'
        lock=False
        return r

    def myWrite(self,cmd):
        global lock
        while lock:
            time.sleep(10e-6)
        lock=True
        if not offline:
            self.inst.write(cmd)
        lock=False

    def updatePlot(self):
        self.line1.set_data(self.X,self.Y1)
        self.line2.set_data(self.X,self.Y2)
        self.ax1.relim(); self.ax1.autoscale_view(scaley=True, scalex=True)
        self.ax2.relim(); self.ax2.autoscale_view(scaley=True, scalex=True)
        self.main.canvas.draw_idle()

    def drawPlot(self):
        time.sleep(1)
        self.line1, = self.ax1.plot(self.X,self.Y1,color='b')
        self.line2, = self.ax2.plot(self.X,self.Y2,color='r')
        self.ax1.set_xlabel('Datetime', fontsize=12)
        self.ax1.tick_params(labelsize=11)
        self.ax1.set_ylabel('Voltage (V)', color='blue', fontsize=12)
        self.ax1.tick_params(axis='y', labelcolor='blue')
        self.ax2.set_ylabel('Current (A)', color='red', fontsize=12)
        self.ax2.tick_params(axis='y', labelcolor='red',labelsize=11)

    def onRampCompletion(self,qty):
        if qty == "VOLT":
            self.main.sVRampB.setEnabled(True)
        elif qty == "CURR":
            self.main.sCRampB.setEnabled(True)

    def refreshF(self):
        val = self.myQuery("*IDN?").split(',')
        try:
            self.title.setText("{} - {}".format(val[0],val[1]))
            b = val[2].split('/')
            self.subTitle.setText("Part#: {}, Serial#: {}, FW ver.: {}".format(b[0],b[1],val[3]))
        except:
            pass
        self.main.sVoltage.setText('{:.3f}'.format(float(self.myQuery("VOLT?"))))
        self.main.sCurrent.setText('{:.3f}'.format(float(self.myQuery("CURR?"))))
        if int(self.myQuery("OUTP:STAT?")) == 1:
            self.main.outB.setStyleSheet("background-color: #00F000;")
        else:
            self.main.outB.setStyleSheet("background-color: #000F00;")

    def rampF(self,qty):
        c = float(self.myQuery("{}?".format(qty)))
        if qty == "VOLT":
            self.main.sVRampB.setEnabled(False)
            s = float(self.main.sVoltage.text().strip())
            if s>32: 
                s=32.0
            n = int(self.main.sVN.text().strip())
            dt = float(self.main.sVdt.text().strip())
        elif qty=="CURR":
            self.main.sCRampB.setEnabled(False)
            s = float(self.main.sCurrent.text().strip())
            if s>10:
                s=10.0
            n = int(self.main.sCN.text().strip())
            dt = float(self.main.sCdt.text().strip())
        vals = np.linspace(c,s,n+1)
        self.worker.setData(self, vals, qty, dt)
        self.worker.start()

    def outF(self):
        val = int(self.myQuery("OUTP:STAT?"))
        self.myWrite("OUTP:STAT {}".format(1-val))
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
        self.myWrite("{}:STEP {}".format(qty,step))
        self.myWrite("{} {}".format(qty,dir))
        
    def update(self):
        self.X.append(datetime.now())
        v = self.myQuery("MEAS:VOLT?")
        c = self.myQuery("MEAS:CURR?")
        self.Y1.append(float(v))
        self.Y2.append(float(c))
        self.main.mVoltage.display(v)        
        self.main.mCurrent.display(c)

    def close(self):
        if not self.inst == None:
            self.inst.close()
        super().close()
        



class DevWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.devWin = uic.loadUi('UIs/devWin.ui', self)
        self.devWin.errText.setVisible(False)
        if not offline:
            self.devWin.okB.setDisabled(True)

        self.devWin.refreshB.clicked.connect(self.refreshF)
        self.devWin.okB.clicked.connect(self.okF)

        if not offline:
            self.rm = pv.ResourceManager()
        else:
            self.rm=None
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
        if not offline:
            keys = self.rm.list_resources()
        else:
            keys=[]
        if len(keys) == 0:
            self.devWin.errText.setVisible(True)
        else:
            self.devWin.errText.setVisible(False)
            self.devWin.okB.setDisabled(False)
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