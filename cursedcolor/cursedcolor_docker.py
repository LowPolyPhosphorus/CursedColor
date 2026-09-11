from krita import DockWidget
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel,
                              QComboBox, QSlider, QCheckBox, QFormLayout,
                              QPushButton, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices
from collections import deque

# --- Windows sensor reading via LibreHardwareMonitor's library, loaded via ---
# --- reflection to work around .NET Framework / .NET Core assembly clashes ---
# Requires in C:\KritaPluginLibs:
#   LibreHardwareMonitorLib.dll (net472 build, from runtimes/win-x64/lib/net472)
#   System.Memory.dll, System.Buffers.dll,
#   System.Numerics.Vectors.dll, System.Runtime.CompilerServices.Unsafe.dll
# Krita must run as Administrator for raw hardware sensor access (CPU temp
# will silently read 0 otherwise).

class HoverMenuButton(QPushButton):
    """A button that opens its menu on hover instead of click."""
    def __init__(self, text, menu):
        super().__init__(text)
        self._menu = menu
        self.setMenu(menu)

    def enterEvent(self, event):
        self.showMenu()
        super().enterEvent(event)

LHM_AVAILABLE = True
_computer = None
_computer_type = None

try:
    import sys
    if r"C:\KritaPluginLibs" not in sys.path:
        sys.path.insert(0, r"C:\KritaPluginLibs")

    import clr
    import System
    from System.Reflection import Assembly
    from System import Activator

    _dll_path = r"C:\KritaPluginLibs\LibreHardwareMonitorLib.dll"
    with open(_dll_path, "rb") as f:
        _dll_bytes = f.read()
    _net_bytes = System.Array[System.Byte](_dll_bytes)
    _assembly = Assembly.Load(_net_bytes)
    _computer_type = _assembly.GetType("LibreHardwareMonitor.Hardware.Computer")
except Exception:
    LHM_AVAILABLE = False


def _get_computer():
    global _computer
    if _computer is None:
        _computer = Activator.CreateInstance(_computer_type)
        _computer_type.GetProperty("IsCpuEnabled").SetValue(_computer, True)
        _computer_type.GetProperty("IsGpuEnabled").SetValue(_computer, True)
        _computer_type.GetMethod("Open").Invoke(_computer, None)
    return _computer


def read_lhm_temps():
    if not LHM_AVAILABLE:
        return None, None

    try:
        computer = _get_computer()
    except Exception:
        return None, None

    cpu_temp = None
    gpu_temp = None

    try:
        hardware_list = _computer_type.GetProperty("Hardware").GetValue(computer)
        for hardware in hardware_list:
            hardware.GetType().GetMethod("Update").Invoke(hardware, None)
            hw_type = str(hardware.GetType().GetProperty("HardwareType").GetValue(hardware)).lower()

            sensors = hardware.GetType().GetProperty("Sensors").GetValue(hardware)
            for sensor in sensors:
                s_type = str(sensor.GetType().GetProperty("SensorType").GetValue(sensor))
                if s_type != "Temperature":
                    continue
                s_value = sensor.GetType().GetProperty("Value").GetValue(sensor)
                if s_value is None:
                    continue
                s_name = (sensor.GetType().GetProperty("Name").GetValue(sensor) or "").lower()

                if "cpu" in hw_type and ("package" in s_name or "tctl" in s_name or "average" in s_name):
                    val = float(s_value)
                    if val > 0:
                        cpu_temp = val

                if "gpu" in hw_type and "core" in s_name and "hot spot" not in s_name:
                    val = float(s_value)
                    if val > 0:
                        gpu_temp = val
    except Exception:
        return None, None

    return cpu_temp, gpu_temp


class CursedColorDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cursed Color")

        tabs = QTabWidget()
        tabs.addTab(self._build_status_tab(), "Status")
        tabs.addTab(self._build_settings_tab(), "Settings")
        self.setWidget(tabs)

        self._delta_history = deque(maxlen=5)
        self._last_smoothed_delta = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(500)

    def _build_status_tab(self):
        w = QWidget()
        layout = QVBoxLayout()
        self.status_label = QLabel("R: -- G: -- B: --")
        self.raw_label = QLabel("CPU: -- °C   GPU: -- °C")
        layout.addWidget(self.status_label)
        layout.addWidget(self.raw_label)

        layout.addStretch()
        layout.addWidget(self._build_help_button())

        w.setLayout(layout)
        return w

    def _build_help_button(self):
        menu = QMenu()

        admin_note = QAction("Run Krita as Administrator for this to work", menu)
        admin_note.setEnabled(False)
        menu.addAction(admin_note)

        menu.addSeparator()

        repo_action = QAction("Check the repo for troubleshooting", menu)
        repo_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/LowPolyPhosphorus/CursedColor"))
        )
        menu.addAction(repo_action)

        button = HoverMenuButton("Why isn't it working?", menu)
        return button

    def _build_settings_tab(self):
        w = QWidget()
        form = QFormLayout()

        self.r_source = QComboBox()
        self.r_source.addItems(["CPU Temp", "GPU Temp", "Delta Rate"])
        form.addRow("R channel source:", self.r_source)

        self.g_source = QComboBox()
        self.g_source.addItems(["CPU Temp", "GPU Temp", "Delta Rate"])
        self.g_source.setCurrentIndex(1)
        form.addRow("G channel source:", self.g_source)

        self.b_source = QComboBox()
        self.b_source.addItems(["CPU Temp", "GPU Temp", "Delta Rate"])
        self.b_source.setCurrentIndex(2)
        form.addRow("B channel source:", self.b_source)

        self.sensitivity = QSlider(Qt.Horizontal)
        self.sensitivity.setRange(1, 200)
        self.sensitivity.setValue(75)
        form.addRow("Delta sensitivity:", self.sensitivity)

        self.drift_rate = QSlider(Qt.Horizontal)
        self.drift_rate.setRange(1, 100)
        self.drift_rate.setValue(20)
        form.addRow("Drift rate:", self.drift_rate)

        self.baseline_temp = QSlider(Qt.Horizontal)
        self.baseline_temp.setRange(20, 80)
        self.baseline_temp.setValue(50)
        form.addRow("Baseline temp (°C):", self.baseline_temp)

        self.apply_to_fg = QCheckBox("Apply to foreground color")
        self.apply_to_fg.setChecked(True)
        form.addRow(self.apply_to_fg)

        w.setLayout(form)
        return w

    def _normalize_temp(self, temp, floor=30.0, ceiling=90.0):
        if temp is None:
            return 0
        pct = (temp - floor) / (ceiling - floor)
        return int(max(0, min(1, pct)) * 255)

    def _compute_delta_rate(self, cpu_temp, gpu_temp, dt=0.5):
        if cpu_temp is None or gpu_temp is None:
            return 0

        raw_delta = cpu_temp - gpu_temp
        self._delta_history.append(raw_delta)
        smoothed = sum(self._delta_history) / len(self._delta_history)

        if self._last_smoothed_delta is None:
            self._last_smoothed_delta = smoothed
            return 0

        rate = (smoothed - self._last_smoothed_delta) / dt
        self._last_smoothed_delta = smoothed

        sensitivity = self.sensitivity.value()
        return int(max(0, min(255, abs(rate) * sensitivity)))

    def _value_for_source(self, source_combo, cpu_val, gpu_val, delta_val):
        choice = source_combo.currentText()
        if choice == "CPU Temp":
            return int(cpu_val)
        elif choice == "GPU Temp":
            return int(gpu_val)
        else:
            return delta_val

    def tick(self):
        cpu_temp, gpu_temp = read_lhm_temps()

        if cpu_temp is None or gpu_temp is None:
            self.raw_label.setText("CPU: -- °C   GPU: -- °C  (sensors not found — is Krita running as Administrator?)")
            return

        self.raw_label.setText(f"CPU: {cpu_temp:.1f} °C   GPU: {gpu_temp:.1f} °C")

        delta_channel = self._compute_delta_rate(cpu_temp, gpu_temp)
        baseline = self.baseline_temp.value()
        rate = self.drift_rate.value()

        cpu_step = (cpu_temp - baseline) * (rate / 100.0) * 0.5
        gpu_step = (gpu_temp - baseline) * (rate / 100.0) * 0.5

        if self.apply_to_fg.isChecked():
            r, g, b = self._shift_foreground_color(cpu_step, gpu_step, delta_channel)
            self.status_label.setText(f"R: {r} G: {g} B: {b}")
        else:
            self.status_label.setText(f"CPU step: {cpu_step:.2f}  GPU step: {gpu_step:.2f}")

    def _shift_foreground_color(self, r_step, g_step, b_target):
        from krita import ManagedColor
        window = Krita.instance().activeWindow()
        if window is None:
            return 0, 0, 0
        view = window.activeView()
        if view is None:
            return 0, 0, 0

        current = view.foregroundColor()
        if current is None:
            cur_r, cur_g, cur_b = 128.0, 128.0, 128.0
        else:
            components = current.components()
            cur_b = components[0] * 255.0
            cur_g = components[1] * 255.0
            cur_r = components[2] * 255.0

        new_r = max(0, min(255, cur_r + r_step))
        new_g = max(0, min(255, cur_g + g_step))
        # B channel still follows delta rate directly since it's already
        # a rate signal, not an absolute reading
        new_b = b_target

        color = ManagedColor("RGBA", "U8", "")
        out_components = color.components()
        out_components[0] = new_b / 255.0
        out_components[1] = new_g / 255.0
        out_components[2] = new_r / 255.0
        out_components[3] = 1.0
        color.setComponents(out_components)
        view.setForeGroundColor(color)

        return int(new_r), int(new_g), int(new_b)

    def canvasChanged(self, canvas):
        pass
