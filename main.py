from PyQt6.QtWidgets import QApplication, QWidget, QSizePolicy, QFileDialog
from PyQt6 import uic
import sys,time
import pyvisa as pv
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from datetime import datetime
import pickle as pk
from pathlib import Path

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
            if self.isInterruptionRequested(): # Check for interruption
                break
            self.mainThread.myWrite("{} {}".format(self.qty,i))
            time.sleep(self.dt)
        self.finished.emit(self.qty)

class MainWindow(QWidget):

    X = []; Y1 = []; Y2 = []
    recIdx = []

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
        self.main.sVRampStopB.clicked.connect(lambda x: self.rampStopF(qty="VOLT"))
        self.main.sCRampStopB.clicked.connect(lambda x: self.rampStopF(qty="CURR"))
        self.main.startLogB.clicked.connect(self.startLogF)
        self.main.browseB.clicked.connect(self.browseF)
        self.main.saveLogB.clicked.connect(self.saveLogF)
        self.main.saveAllB.clicked.connect(self.saveAllF)
        self.main.clearB.clicked.connect(self.clearF)
        self.main.refreshB.clicked.connect(self.refreshF)
        self.main.pauseAllB.clicked.connect(self.pauseAllF)
        self.main.sVoltage.returnPressed.connect(lambda: self.directSetF(qty="VOLT"))
        self.main.sCurrent.returnPressed.connect(lambda: self.directSetF(qty="CURR"))

        self.dir = Path.home() / 'Desktop'
        self.main.fileName.setText(f'{self.dir / "cathodePS.txt"}')

        if not offline:
            self.rm = pv.ResourceManager()
            self.inst = self.rm.open_resource(dev)
        else:
            self.rm = None
            self.inst = None

        self.refreshF()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(10) # auto update time in ms

        self.fig = Figure(); 
        self.ax1 = self.fig.add_subplot(); self.ax2 = self.ax1.twinx()
        self.drawPlot()

        self.main.canvas = FigureCanvasQTAgg(self.fig)
        self.main.canvas.setSizePolicy(heve)
        self.main.layout().addWidget(self.main.canvas,16,0,1,11)
        
        self.timer2 = QTimer(self)
        self.timer2.timeout.connect(self.updatePlot)
        self.timer2.start(1000) # auto update time in ms

        self.worker = Worker()
        self.worker.finished.connect(self.onRampCompletion)

    def directSetF(self,qty):
        if qty=="VOLT":
            try:
                s = float(self.main.sVoltage.text().strip())
            except:
                self.main.sVoltage.setStyleSheet("color: red; font-weight: bold;")
                return
            self.main.sVoltage.setStyleSheet(None)
            if s>32:
                s=32.0
            elif s<0:
                s=0.0
            self.main.sVoltage.setText(f"{s:.03f}")
        elif qty=="CURR":
            try:
                s = float(self.main.sCurrent.text().strip())
            except:
                self.main.sCurrent.setStyleSheet("color: red; font-weight: bold;")
                return
            self.main.sCurrent.setStyleSheet(None)
            if s>10:
                s=10.0
            elif s<0:
                s=0.0
            self.main.sCurrent.setText(f"{s:.03f}")
        self.myWrite("{} {}".format(qty,s))


    def pauseAllF(self):
        if self.main.pauseAllB.isChecked():
            self.main.pauseAllB.setStyleSheet("background-color: yellow; color: black;")
            self.timer.stop()
            self.updatePlot()
            self.timer2.stop()
        else:
            self.main.pauseAllB.setStyleSheet(None)
            self.timer.start()
            self.timer2.start()

    def clearF(self):
        global lock
        while lock:
            time.sleep(1e-6)
        lock=True
        self.X = []; self.Y1 = []; self.Y2 = []
        self.updatePlot()
        lock=False

    def startLogF(self):            
        global lock
        self.main.clearB.setDisabled(True)
        while lock:
            time.sleep(1e-6)
        lock=True
        self.recIdx.append(self.X[-1])
        self.ax1.text(self.X[-1],self.Y1[-1],'|',color='orange',fontsize=20,fontweight='bold')
        self.ax2.text(self.X[-1],self.Y2[-1],'|',color='orange',fontsize=20,fontweight='bold')
        lock=False
        if self.main.startLogB.isChecked():
            self.main.startLogB.setStyleSheet("background-color: #00FF00;color: black;")
        else:
            self.main.startLogB.setStyleSheet("background-color: #001A00;color: white;")

    def browseF(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Choose a filename", f'{self.dir}', "All Files (*);;Text Files (*.txt);;CSV Files (*.csv)")
        if fileName:
            self.main.fileName.setText(fileName)

    def saveLogF(self):
        global lock
        if (len(self.recIdx) == 0) or (self.main.fileName.text().strip() == "") :
            return
        if not len(self.recIdx)%2 == 0:
            self.startLogB.setChecked(False)
            self.startLogF()
        while lock:
            time.sleep(1e-6)
        lock=True
        X=[];Y1=[];Y2=[]
        for i in range(0,len(self.recIdx),2):
            a = self.X.index(self.recIdx[i])
            b = self.X.index(self.recIdx[i+1])+1
            X += self.X[a:b]
            Y1 += self.Y1[a:b]
            Y2 += self.Y2[a:b]
        self.recIdx=[]
        lock=False
        with open(self.main.fileName.text(), 'w') as F:
            for item1, item2, item3 in zip(X, Y1, Y2):
                F.write(f"{item1},{item2},{item3}\n")
        self.main.clearB.setDisabled(False)
    
    def saveAllF(self):
        global lock
        if (self.main.fileName.text().strip() == "") :
            return
        while lock:
            time.sleep(1e-6)
        lock=True
        with open(self.main.fileName.text(), 'w') as F:
            for item1, item2, item3 in zip(self.X, self.Y1, self.Y2):
                F.write(f"{item1},{item2},{item3}\n")
        lock=False
        self.main.clearB.setDisabled(False)
    
    def myQuery(self,cmd):
        global lock
        while lock:
            time.sleep(1e-6)
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
            time.sleep(1e-6)
        lock=True
        if not offline:
            self.inst.write(cmd)
        lock=False

    def updatePlot(self):
        self.line1.set_data(self.X,self.Y1)
        self.line2.set_data(self.X,self.Y2)
        self.ax1.relim(); self.ax1.autoscale_view(scaley=True, scalex=True)
        self.ax2.relim(); self.ax2.autoscale_view(scaley=True, scalex=True)
        a = (sys.getsizeof(self.X)/1024 + sys.getsizeof(self.Y1)/1024 + sys.getsizeof(self.Y2)/1024)/1024
        self.main.size.setText(f"{a:0.2f} MB")
        self.main.canvas.draw_idle()


    def drawPlot(self):
        time.sleep(1)
        self.line1, = self.ax1.plot(self.X,self.Y1,color='b',alpha=0.4)
        self.line2, = self.ax2.plot(self.X,self.Y2,color='r',alpha=0.4)
        # self.line3, = self.ax1.plot((),(),color='c',lw=1.75,alpha=0.4)
        # self.line4, = self.ax2.plot((),(),color='m',lw=1.75,alpha=0.4)
        self.ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()
        self.ax1.set_xlabel('Time', fontsize=12)
        self.ax1.tick_params(labelsize=11)
        self.ax1.set_ylabel('Voltage (V)', color='blue', fontsize=12)
        self.ax1.tick_params(axis='y', labelcolor='blue')
        self.ax2.set_ylabel('Current (A)', color='red', fontsize=12)
        self.ax2.tick_params(axis='y', labelcolor='red',labelsize=11)
        self.ax1.grid('x')

    def rampStopF(self,qty):
        self.worker.requestInterruption()
        self.worker.finished.emit(qty)
        
    def onRampCompletion(self,qty):
        if qty == "VOLT":
            self.main.sVRampB.setEnabled(True)
            self.main.sVoltage.setText('{:0.3f}'.format(float(self.myQuery("VOLT?"))))
        elif qty == "CURR":
            self.main.sCRampB.setEnabled(True)
            self.main.sCurrent.setText('{:0.3f}'.format(float(self.myQuery("CURR?"))))

    def rampF(self,qty):
        if qty == "VOLT":
            try:
                s = float(self.main.sVRampVal.text().strip())
            except:
                self.main.sVRampVal.setStyleSheet("color: red; font-weight: bold;")
                return
            self.main.sVRampVal.setStyleSheet(None)
            if s>32: 
                s=32.0
                self.main.sVRampVal.setText('32.000')
            try:
                n = int(self.main.sVN.text().strip())
            except:
                self.main.sVN.setStyleSheet("color: red; font-weight: bold;")
                return
            self.main.sVN.setStyleSheet(None)
            try:
                dt = float(self.main.sVdt.text().strip())
            except:
                self.main.sVdt.setStyleSheet("color: red; font-weight: bold;")
                return
            self.main.sVdt.setStyleSheet(None)
            self.main.sVRampB.setEnabled(False)
        elif qty=="CURR":
            try:
                s = float(self.main.sCRampVal.text().strip())
            except:
                self.main.sCRampVal.setStyleSheet("color: red; font-weight: bold;")
                return
            self.main.sCRampVal.setStyleSheet(None)
            if s>10:
                s=10.0
                self.main.sCRampVal.setText('10.000')
            try:
                n = int(self.main.sCN.text().strip())
            except:
                self.main.sCN.setStyleSheet("color: red; font-weight: bold;")
                return
            self.main.sCN.setStyleSheet(None)
            try:
                dt = float(self.main.sCdt.text().strip())
            except:
                self.main.sCdt.setStyleSheet("color: red; font-weight: bold;")
                return
            self.main.sCdt.setStyleSheet(None)
            self.main.sCRampB.setEnabled(False)
        c = float(self.myQuery("{}?".format(qty)))
        vals = np.linspace(c,s,n+1)
        self.worker.setData(self, vals, qty, dt)
        self.worker.start()

    def outF(self):
        val = int(self.myQuery("OUTP:STAT?"))
        self.myWrite("OUTP:STAT {}".format(1-val))
        if val == 1:    # already on, turn it off
            self.main.outB.setStyleSheet("background-color: #001A00;")
        else:
            self.main.outB.setStyleSheet("background-color: #00FF00;")

    def stepUD(self,qty,dir):
        if qty == "VOLT":
            if self.main.sVCoarse.value() == 0:
                step = 0.01
            elif self.main.sVCoarse.value() == 1:
                step = 0.1
            else:
                step=1
            if dir == "UP":
                nv=float(self.main.sVoltage.text())+step
                if nv>32:
                    nv=32.0
                self.main.sVoltage.setText('{:0.3f}'.format(nv))
            else:
                nv=float(self.main.sVoltage.text())-step
                if nv<0:
                    nv=0.0
                self.main.sVoltage.setText('{:0.3f}'.format(nv))
        elif qty=="CURR":
            if self.main.sCCoarse.value() == 0:
                step=0.01
            elif self.main.sCCoarse.value() == 1:
                step=0.1
            else:
                step=1
            if dir == "UP":
                nv=float(self.main.sCurrent.text())+step
                if nv>10:
                    nv=10.0
                self.main.sCurrent.setText('{:0.3f}'.format(nv))
            else:
                nv=float(self.main.sCurrent.text())-step
                if nv<0:
                    nv=0.0
                self.main.sCurrent.setText('{:0.3f}'.format(nv))
        self.myWrite("{}:STEP {}".format(qty,step))
        self.myWrite("{} {}".format(qty,dir))
        
    def update(self):
        global lock
        while lock:
            time.sleep(1.e-6)
        lock = True
        self.X.append(datetime.now())
        if not offline:
            v = self.inst.query("MEAS:VOLT?").strip()
            c = self.inst.query("MEAS:CURR?").strip()
        else:
            v='0.0';c='0.0'
        self.Y1.append(float(v))
        self.Y2.append(float(c))
        lock = False
        self.main.mVoltage.display(v)        
        self.main.mCurrent.display(c)
        self.main.mPower.display(self.myQuery("MEAS:POW?"))
        sv=float(self.myQuery("VOLT?"))
        if sv>0:
            if abs(float(v)-sv)/sv > 0.1:
                self.main.mVoltage.setStyleSheet('color: red;')
            else:
                self.main.mVoltage.setStyleSheet('color: green;')
        else:
            self.main.mVoltage.setStyleSheet('color: black;')
        sv=float(self.myQuery("CURR?"))
        if sv>0:
            if abs(float(c)-sv)/sv > 0.1:
                self.main.mCurrent.setStyleSheet('color: red;')
            else:
                self.main.mCurrent.setStyleSheet('color: green;')
        else:
            self.main.mCurrent.setStyleSheet('color: black;')


    def refreshF(self):
        val = self.myQuery("*IDN?").split(',')
        try:
            self.title.setText("{} - {}".format(val[0],val[1]))
            b = val[2].split('/')
            self.subTitle.setText("Part#: {}, Serial#: {}, FW ver.: {}".format(b[0],b[1],val[3]))
        except:
            pass
        self.main.sVoltage.setText('{:0.3f}'.format(float(self.myQuery("VOLT?"))))
        self.main.sCurrent.setText('{:0.3f}'.format(float(self.myQuery("CURR?"))))
        if int(self.myQuery("OUTP:STAT?")) == 1:
            self.main.outB.setStyleSheet("background-color: #00FF00;")
        else:
            self.main.outB.setStyleSheet("background-color: #001A00;")
    
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