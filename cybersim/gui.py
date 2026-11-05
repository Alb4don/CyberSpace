import threading
from pathlib import Path
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QSplitter, QFileDialog, QSlider, QProgressBar
import pyqtgraph as pg
from .models import Config
from .engine import Engine
from .evaluation import export_csv

class Worker(QObject):
    frame = Signal(object)
    completed = Signal(object)
    failed = Signal()
    finished = Signal()

    def __init__(self, config, database, delay):
        super().__init__()
        self.config = config
        self.database = database
        self.delay = delay
        self.resume = threading.Event()
        self.resume.set()
        self.stop = threading.Event()

    @Slot()
    def run(self):
        try:
            for kind, payload in Engine(self.config, self.database).stream():
                while not self.resume.wait(0.05):
                    if self.stop.is_set():
                        break
                if self.stop.is_set():
                    break
                if kind == 'frame':
                    self.frame.emit(payload)
                    if self.stop.wait(self.delay):
                        break
                else:
                    self.completed.emit(payload)
        except Exception:
            self.failed.emit()
        finally:
            self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self, database: Path):
        super().__init__()
        self.database = database
        self.metrics = None
        self.thread = None
        self.worker = None
        self.traces = []
        self.setWindowTitle('Autonomous Reconnaissance Laboratory')
        self.resize(1380, 850)
        self.setStyleSheet('QMainWindow,QWidget{background:#101923;color:#dce6f2;font-size:13px} QPushButton{background:#203e52;border:1px solid #36576c;padding:8px;border-radius:5px} QPushButton:disabled{color:#607485} QSpinBox,QDoubleSpinBox{background:#1c2c3a;padding:6px;border:1px solid #375064} QPlainTextEdit{background:#14212d;border:1px solid #30465c} QProgressBar{background:#1b2b38;border:0;height:9px} QProgressBar::chunk{background:#4cb7b5}')
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        header = QHBoxLayout()
        self.steps = QSpinBox()
        self.steps.setRange(1, 200)
        self.steps.setValue(60)
        self.agents = QSpinBox()
        self.agents.setRange(1, 16)
        self.agents.setValue(4)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.01, 1.0)
        self.threshold.setSingleStep(0.05)
        self.threshold.setValue(0.72)
        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(1, 20)
        self.speed.setValue(5)
        self.speed.setFixedWidth(115)
        for label, control in [('Steps', self.steps), ('Agents', self.agents), ('Confidence', self.threshold), ('Speed', self.speed)]:
            header.addWidget(QLabel(label))
            header.addWidget(control)
        self.run_button = QPushButton('START')
        self.run_button.clicked.connect(self.start)
        self.pause_button = QPushButton('PAUSE')
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause)
        self.stop_button = QPushButton('STOP')
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop)
        self.export_button = QPushButton('EXPORT CSV')
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export)
        for button in (self.run_button, self.pause_button, self.stop_button, self.export_button):
            header.addWidget(button)
        layout.addLayout(header)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.plot = pg.PlotWidget()
        self.plot.setBackground('#101923')
        self.plot.showGrid(x=True, y=True, alpha=0.12)
        self.plot.setAspectLocked(True)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlainText('SIMULATION READY\nSynthetic offline environment only.')
        splitter.addWidget(self.plot)
        splitter.addWidget(self.log)
        splitter.setSizes([980, 360])
        layout.addWidget(splitter)
        self.statusBar().showMessage('Ready · no external network access')

    @Slot()
    def start(self):
        if self.thread is not None:
            return
        self.metrics = None
        self.traces = []
        self.progress.setValue(0)
        self.log.clear()
        self.run_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.export_button.setEnabled(False)
        config = Config(steps=self.steps.value(), agents=self.agents.value(), threshold=self.threshold.value())
        self.thread = QThread(self)
        self.worker = Worker(config, self.database, 0.9 / self.speed.value())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.frame.connect(self.display_frame)
        self.worker.completed.connect(self.display)
        self.worker.failed.connect(self.failure)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.ready)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.statusBar().showMessage('Agents exploring the simulated environment')

    @Slot()
    def pause(self):
        if self.worker is None:
            return
        if self.worker.resume.is_set():
            self.worker.resume.clear()
            self.pause_button.setText('RESUME')
            self.statusBar().showMessage('Paused')
        else:
            self.worker.resume.set()
            self.pause_button.setText('PAUSE')
            self.statusBar().showMessage('Running')

    @Slot()
    def stop(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.worker.resume.set()
            self.statusBar().showMessage('Stopping simulation')

    @Slot()
    def ready(self):
        self.thread = None
        self.worker = None
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText('PAUSE')
        self.stop_button.setEnabled(False)

    @Slot()
    def failure(self):
        self.log.appendPlainText('Simulation failed. Review local diagnostics.')
        self.statusBar().showMessage('Simulation failed')

    @Slot(object)
    def display_frame(self, frame):
        self.progress.setValue(round(100 * frame['step'] / frame['total']))
        self.plot.clear()
        positions = {name: (x + 0.25 * z, y + 0.15 * z) for name, x, y, z, _, _ in frame['nodes']}
        for source, destination, active, relation in frame['edges']:
            a, b = positions[source], positions[destination]
            color = '#36566b' if active else '#713e48'
            self.plot.plot([a[0], b[0]], [a[1], b[1]], pen=pg.mkPen(color, width=1.5, style=Qt.PenStyle.SolidLine if active else Qt.PenStyle.DashLine))
        for path in frame['paths']:
            for a, b in zip(path['path'], path['path'][1:]):
                x, y = positions[a], positions[b]
                self.plot.plot([x[0], y[0]], [x[1], y[1]], pen=pg.mkPen('#e9ba64', width=3))
        for name, x, y, z, target, active in frame['nodes']:
            color = '#6ac7ed' if active else '#67727f'
            if target:
                color = '#e8a95c' if active else '#886b54'
            self.plot.plot([positions[name][0]], [positions[name][1]], pen=None, symbol='o', symbolSize=19,
                symbolBrush=pg.mkBrush(color), symbolPen=pg.mkPen('#dceaf3', width=1))
            label = pg.TextItem(name, color='#dce6f2', anchor=(0.5, -0.35))
            label.setPos(*positions[name])
            self.plot.addItem(label)
        palette = ['#f46e9a', '#9de16e', '#b58bff', '#ffe07e', '#68ddd0', '#f58b66']
        for i, node in enumerate(frame['agents']):
            x, y = positions[node]
            offset = (i % 4 - 1.5) * 0.24
            self.plot.plot([x + offset], [y + 0.38 + (i // 4) * 0.2], pen=None, symbol='t', symbolSize=18,
                symbolBrush=pg.mkBrush(palette[i % len(palette)]), symbolPen=pg.mkPen('#ffffff', width=1))
        self.traces.extend(frame['events'])
        self.traces = self.traces[-160:]
        summary = [f"STEP {frame['step']}/{frame['total']} · EPOCH {frame['epoch']}",
            f"OBSERVATIONS EXPANDED: {frame['expanded']}", f"VERIFIED PATHS: {len(frame['paths'])}", '']
        summary.extend(' → '.join(item['path']) for item in frame['paths'][:8])
        summary.extend(['', 'LIVE AGENT ACTIVITY', *self.traces[-45:]])
        self.log.setPlainText('\n'.join(summary))
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.statusBar().showMessage(f"Step {frame['step']}/{frame['total']} · {len(frame['paths'])} verified paths · offline")

    @Slot(object)
    def display(self, result):
        _, findings, metrics, episode = result
        self.metrics = metrics
        self.export_button.setEnabled(True)
        self.log.appendPlainText(f'\nEPISODE {episode} COMPLETE')
        for metric in metrics:
            self.log.appendPlainText(f'{metric.method}: coverage={metric.coverage:.2%}, FPR={metric.false_positive_rate:.2%}, expanded={metric.nodes_expanded}, time={metric.wall_seconds:.4f}s')
        self.statusBar().showMessage('Simulation complete')

    @Slot()
    def export(self):
        if self.metrics is None:
            return
        filename, _ = QFileDialog.getSaveFileName(self, 'Export metrics', 'evaluation.csv', 'CSV (*.csv)')
        if filename:
            try:
                export_csv(Path(filename), self.metrics)
                self.statusBar().showMessage('Metrics exported')
            except OSError:
                self.statusBar().showMessage('Export failed')

def launch(database: Path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(database)
    window.show()
    return app.exec()
