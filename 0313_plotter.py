from PyQt6.QtWidgets import (QMainWindow, QPushButton, QWidget, QLineEdit,
                             QGridLayout, QApplication, QGraphicsWidget,
                             QLabel, QRadioButton)
import sys
import numpy as np
import serial
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
import pandas as pd
import datetime
import serial.tools.list_ports

# インスタンス変数　オブジェクトごとに違う値をとる。
# クラス変数　オブジェクト同士で共通の値をとる。
# 両方，クラスの中からは，self.変数名でアクセスできる。
# メソッドの中の一時的な変数

# カレントディレクトリは(jupyter)の仮想環境が動いているディレクトリなので注意


class Window(QMainWindow):

    SAMPRING_RATE = 10000  # USB通信からのサンプリング周波数
    MICRO_TO_UNIT = 1000000  # μ秒から秒に行く定数
    DATA_LENGTH = int(2**20)  # 最大のデータ長
    SAFE_WAIT_FACTOR = 1000  # タイマースタートの待ち時間に対する安全率
    BAUDRATE = 115200  # USBシリアルのボーレート。最大115200
    style = """
    QPushButton {
        border: none;
        background-color: #3498db;
        color: #fff;
        padding: 10px 20px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #2980b9;
    }
    QPushButton:pressed {
        background-color: #1b4f72;
    }
    """

    # たぶんmicrosがオーバーフローするところまでのデータ長にしておけばいい
    # FGが律速（20Hz）なので，サンプリング周波数はそれくらいで十分

    def __init__(self):  # コンストラクタ
        super().__init__()  # 継承しているQMainWindow classのインスタンス変数とメソッドを呼ぶ

        # ウィンドウの設定
        self.setWindowTitle("KES-F System")  # インスタンスに対してウィンドウタイトルを設定
        self.setGeometry(100, 100, 800, 450)  # インスタンスに対して初期位置とサイズを指定

        #ウィジェット・レイアウト
        self.widget = QWidget()  # インスタンス変数としてウィジェットを作成
        self.widget_for_time_series = pg.GraphicsLayoutWidget(show=True)
        self.widget_for_comport = QWidget()
        self.widget_for_controller = QWidget()

        self.setCentralWidget(self.widget)

        self.widget_for_time_series.setMinimumSize(800, 450)

        self.layout = QGridLayout()  # レイアウト１を作成
        self.widget.setLayout(self.layout)

        self.layout2 = QGridLayout()  # レイアウト２を作成
        self.widget_for_comport.setLayout(self.layout2)

        self.layout3 = QGridLayout()
        self.widget_for_controller.setLayout(self.layout3)

        # フォントの設定(UiComponentsより前じゃないといけない)
        self.btn_font = QtGui.QFont()
        self.btn_font.setFamily('Yu Gothic UI')
        self.btn_font.setPointSize(12)

        self.UiComponents()  # Uiの要素を表示する
        self.plot_with_respect_to_time()  # 時系列プロット関数

        self.layout.addWidget(self.widget_for_time_series, 0,
                              1)  # レイアウトに時系列プロットを追加
        self.layout.addWidget(self.widget_for_comport, 0,
                              0)  # レイアウトにCOMポートの選択ツールを追加

        self.layout.addWidget(self.save, 2, 0)  # レイアウトに保存ボタン
        self.layout.addWidget(self.plot_start, 3, 0)  # レイアウトにプロットのスタートボタン
        self.layout.addWidget(self.plot_stop, 4, 0)  # レイアウトにプロットのストップボタン
        self.layout.addWidget(self.re_start, 5, 0)  # レイアウトにプロットの再スタートボタン
        self.layout.addWidget(self.exit, 6, 0)  # レイアウトに終了ボタン

        self.layout.addWidget(self.widget_for_controller, 2, 1, 4, 1)

        self.layout.addWidget(self.line, 2, 1)  # レイアウトに保存ファイル名のテキストボックス

        self.layout2.addWidget(QLabel(), 3, 0)  # レイアウト２に逆回転のチェックを追加

        self.layout3.addWidget(self.motor_start, 0, 0)
        self.layout3.addWidget(self.motor_stop, 0, 1)
        self.layout3.addWidget(self.motor_reverse, 0, 2)

        self.layout.addWidget(self.message_box, 6, 1)

        self.show()

    def UiComponents(self):
        self.save = Button('save', self.save_func)
        # self.save.setIcon(QtGui.QIcon('1069_dl_h.png'))

        self.plot_start = Button('start', self.plot_start_func, False)
        self.plot_start.setFixedSize(120, 40)

        self.plot_stop = Button('stop', self.plot_stop_func, False)

        self.re_start = Button('re start', self.re_start_func, False)

        self.exit = Button('exit', self.exit_meth)

        self.motor_start = Button('まわす', self.motor_start_func)

        self.motor_stop = Button('とめる', self.motor_stop_func)

        self.motor_reverse = Button('逆回転', self.counter_rotate)

        dt = datetime.datetime.now()
        line_text = dt.strftime('%Y%m%d%H%M')
        self.line = QLineEdit(line_text)  # 保存ファイル名のテキストボックス
        self.line.setFont(QtGui.QFont('Yu Gothic UI', 10))

        self.message_box = QLabel('シリアルポートを選択してください')

        self.select_comport()  # COMポートに関する関数

    def save_func(self):  # 保存関数
        array = []
        array = np.append(self.t, self.y1)
        array = np.append(array, self.y2)
        array = np.append(array, self.y3)
        array = np.append(array, self.y4)
        array = np.reshape(array, (5, len(self.t)))  # 5行×(サンプル数)列のarrayに整形
        array = np.transpose(array)  # 転置する->(サンプル数)行×5
        data = pd.DataFrame(
            array, columns=['Time', 'F1', 'F2', 'Displacement', 'Sensor'])
        data.to_csv(str(self.line.text()) + '.csv')

    def plot_start_func(self):  # プロットのスタート関数
        self.wait_time = (1 / self.SAMPRING_RATE) * self.SAFE_WAIT_FACTOR
        self.plot_stop.setEnabled(True)
        try:
            self.ser.write(b'0')  # 0を送るとプロット開始
            self.plot_start.setText('working...')
        except Exception:
            self.plot_start.setText('EROOR')
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(int(self.wait_time))  # スタート少し待つ。

    def plot_stop_func(self):  # プロットのストップ関数
        self.timer.stop()
        self.plot_stop.setEnabled(False)
        self.plot_start.setStyleSheet(""" """)
        self.ser.write(b'1')  # 1を送るとプロット終了
        self.re_start.setEnabled(True)
        self.re_start.setStyleSheet(self.style)
        # ここでは，シリアルをcloseしない。

    def re_start_func(self):  # リセット関数
        self.timer.stop()

        self.num = 0

        self.t = np.array([])
        self.y1 = np.array([])
        self.y2 = np.array([])
        self.y3 = np.array([])
        self.y4 = np.array([])

        self.curve.setData(self.t, self.y1)
        self.curve2.setData(self.t, self.y2)
        self.curve3.setData(self.t, self.y3)
        self.curve4.setData(self.t, self.y4)

        self.plot_start_func()

    def motor_start_func(self):
        self.ser.write(b'3')

    def motor_stop_func(self):
        self.ser.write(b'4')

    def counter_rotate(self):  # 逆回転関数
        self.ser.write(b'5')  # 5を送る

    def open_and_check_serial(self, comport):
        try:
            self.ser = serial.Serial(comport, self.BAUDRATE)
            self.message_box.setText('シリアルポートを開きました')
        except Exception as e:
            self.message_box.setText(str(e))
        # if self.ser.isOpen():
        #     print("Serial port opened successfully.")
        #     return self.ser
        # else:
        #     print("Failed to open serial port.")
        #     return None

    def com_port_func(self):
        ports = list(serial.tools.list_ports.comports())
        portNames = []
        for ps in ports:
            portNow = ps.device
            portNames.append(portNow)
        return portNames
        # portNowDiscription = ports[0].discription

    def select_comport(self):
        portNames = self.com_port_func()
        i = 0
        for p in portNames:
            btntmp = QRadioButton(p)
            btntmp.com = p
            btntmp.released.connect(self.onClickedRadioButton)
            self.layout2.addWidget(btntmp, i, 0)
            i = i + 1

    def onClickedRadioButton(self):
        radio_clicked_now = self.widget_for_comport.sender()
        self.comport = radio_clicked_now.com
        self.plot_start.setEnabled(True)
        self.plot_start.setStyleSheet(self.style)
        self.open_and_check_serial(self.comport)
        return self.comport

    def setGraphMultipleAxis(self, p1, p2, p3, p4, ax4):
        p1.showAxis('right')
        p1.scene().addItem(p2)
        p1.scene().addItem(p3)
        p1.getAxis('left').linkToView(p2)
        p1.getAxis('right').linkToView(p3)
        p2.setXLink(p1)
        p2.setYLink(p1)
        p3.setXLink(p1)
        p2.sigRangeChanged.connect(
            lambda: p2.setGeometry(p1.vb.sceneBoundingRect()))
        p3.sigRangeChanged.connect(
            lambda: p3.setGeometry(p1.vb.sceneBoundingRect()))

        if p4 is not None and ax4 is not None:
            spacer = QGraphicsWidget()
            spacer.setMaximumSize(15, 15)
            p1.layout.addItem(spacer, 2, 3)

            p1.layout.addItem(ax4, 2, 4)
            p1.scene().addItem(p4)
            ax4.linkToView(p4)
            p4.setXLink(p1)

            p4.sigRangeChanged.connect(
                lambda: p4.setGeometry(p1.vb.sceneBoundingRect()))

    def setGraphFrameFont(self, p1, ax4):
        self.font = QtGui.QFont()
        self.font.setPointSize(12)
        self.fontFamily = 'Yu Gothic UI'
        self.font.setFamily(self.fontFamily)
        p1.getAxis('bottom').setStyle(tickFont=self.font)
        p1.getAxis('bottom').setTextPen('#FFF')
        p1.getAxis('left').setStyle(tickFont=self.font)
        p1.getAxis('left').setTextPen('#FFF')
        p1.getAxis('right').setStyle(tickFont=self.font)
        p1.getAxis('right').setTextPen('#FFF')
        ax4.setStyle(tickFont=self.font)
        ax4.setTextPen('#FFF')
        p1.getAxis('bottom').setHeight(3.5 * 12)
        p1.getAxis('left').setWidth(4 * 12)
        p1.getAxis('right').setWidth(4.3 * 12)
        ax4.setWidth(6 * 12)

    def plot_with_respect_to_time(self):
        # plotItem
        graph1 = self.widget_for_time_series.addPlot(row=0, col=0)
        graph2 = pg.PlotCurveItem(title="Force", pen=(153, 221, 255))
        p2 = pg.ViewBox()
        p2.addItem(graph2)
        graph3 = pg.PlotCurveItem(title="Disp", pen=(181, 255, 20))
        p3 = pg.ViewBox()
        p3.addItem(graph3)
        graph4 = pg.PlotCurveItem(title="Sensor", pen='y')
        p4 = pg.ViewBox()
        p4.addItem(graph4)
        ax4 = pg.AxisItem(orientation='right')
        self.setGraphMultipleAxis(graph1, p2, p3, p4, ax4)
        self.setGraphFrameFont(graph1, ax4)

        label = f'<font face={self.fontFamily}>Time / s</font>'
        label1 = f'<font face={self.fontFamily}>Force / N</font>'
        label2 = f'<font face={self.fontFamily}>Displacement / mm</font>'
        label3 = f'<font face={self.fontFamily}>Sensor Output / mV</font>'

        labelstyle = {'color': '#FFF', 'font-size': '12pt'}

        graph1.setLabel('left', label1, **labelstyle)
        graph1.setLabel('right', label2, **labelstyle)
        graph1.setLabel('bottom', label, **labelstyle)
        ax4.setLabel(label3, **labelstyle)

        graph1.setXRange(0, 50, padding=0)
        graph1.setYRange(-10, 10, padding=0)
        # p1.setRange(yRange = (-10, 10), padding = 0)
        p2.setRange(yRange=(-10, 10), padding=0)
        p3.setRange(yRange=(-10, 10), padding=0)
        p4.setRange(yRange=(150, 1750), padding=0)

        self.num = 0

        # 適当なyデータ
        self.t = np.array([])
        self.y1 = np.array([])
        self.y2 = np.array([])
        self.y3 = np.array([])
        self.y4 = np.array([])

        self.curve = graph1.plot(pen=(221, 238, 255))
        self.curve2 = graph2
        self.curve3 = graph3
        self.curve4 = graph4
        pg.setConfigOptions(antialias=True)

        # self.widget_for_comport.setStyleSheet("background-color:red;")

    def update(self):
        if self.num == 0:
            input_serial = self.ser.readline().rstrip()
            try:
                input = input_serial.decode()
                tmp1, tmp2, tmp3, tmp4, tmp5 = input.split(",")
                tmp1 = float(tmp1)
                tmp2 = float(tmp2)
                tmp3 = float(tmp3)
                tmp4 = float(tmp4)
                tmp5 = float(tmp5) / self.MICRO_TO_UNIT
                self.t0 = tmp5
                self.y1 = np.append(self.y1, tmp1)
                self.y2 = np.append(self.y2, tmp2)
                self.y3 = np.append(self.y3, tmp3)
                self.y4 = np.append(self.y4, tmp4)
                self.t = np.append(self.t, 0)
                self.curve.setData(self.t, self.y1)
                self.curve2.setData(self.t, self.y2)
                self.curve3.setData(self.t, self.y3)
                self.curve4.setData(self.t, self.y4)
                self.num += 1
            except (ValueError, UnicodeDecodeError):
                tmp1 = 0
                tmp2 = 0
                tmp3 = 0
                tmp4 = 0
                self.y1 = np.append(self.y1, tmp1)
                self.y2 = np.append(self.y2, tmp2)
                self.y3 = np.append(self.y3, tmp3)
                self.y4 = np.append(self.y4, tmp4)
                self.t = np.append(self.t, tmp5)
                self.curve.setData(self.t, self.y1)
                self.curve2.setData(self.t, self.y2)
                self.curve3.setData(self.t, self.y3)
                self.curve4.setData(self.t, self.y4)
                self.num += 1
        elif 0 < self.num < self.DATA_LENGTH:
            input_serial = self.ser.readline().rstrip()
            try:
                input = input_serial.decode()
                tmp1, tmp2, tmp3, tmp4, tmp5 = input.split(",")
                tmp1 = float(tmp1)
                tmp2 = float(tmp2)
                tmp3 = float(tmp3)
                tmp4 = float(tmp4)
                tmp5 = float(tmp5) / self.MICRO_TO_UNIT - self.t0
                self.y1 = np.append(self.y1, tmp1)
                self.y2 = np.append(self.y2, tmp2)
                self.y3 = np.append(self.y3, tmp3)
                self.y4 = np.append(self.y4, tmp4)
                self.t = np.append(self.t, tmp5)
                self.curve.setData(self.t, self.y1)
                self.curve2.setData(self.t, self.y2)
                self.curve3.setData(self.t, self.y3)
                self.curve4.setData(self.t, self.y4)
                self.num += 1
            except (ValueError, UnicodeDecodeError):
                tmp1 = 0
                tmp2 = 0
                tmp3 = 0
                tmp4 = 0
                self.y1 = np.append(self.y1, tmp1)
                self.y2 = np.append(self.y2, tmp2)
                self.y3 = np.append(self.y3, tmp3)
                self.y4 = np.append(self.y4, tmp4)
                self.t = np.append(self.t, tmp5)
                self.curve.setData(self.t, self.y1)
                self.curve2.setData(self.t, self.y2)
                self.curve3.setData(self.t, self.y3)
                self.curve4.setData(self.t, self.y4)
                self.num += 1
        else:
            self.timer.stop()

    def exit_meth(self):
        try:
            self.timer.stop()
            self.ser.close()
        except Exception:
            pass
        finally:
            sys.exit(App.exec())


class Button(QPushButton):

    def __init__(self, text, func, is_enabled=True):
        super().__init__(None)

        self.setText(text)
        self.clicked.connect(func)

        btn_font = QtGui.QFont()
        btn_font.setFamily('Yu Gothic UI')
        btn_font.setPointSize(12)
        self.setFont(btn_font)

        self.setEnabled(is_enabled)


# PyQT6のアプリケーションオブジェクト
App = QApplication(sys.argv)
# インスタンス生成
window = Window()
# スタートさせる??
sys.exit(App.exec())
