import os
import sys
import time
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QAction, QIcon
from PyQt6.QtWidgets import QApplication, QLabel, QMenu, QVBoxLayout, QWidget
from pynput import keyboard, mouse
import psutil
import pygetwindow as gw

os.environ['QT_LOGGING_RULES'] = 'qt.qpa.window=false'

# PyInstaller로 묶었을 때와 일반 실행일 때 모두 아이콘/파일 경로를 찾는 함수
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 이번 1초 동안 입력이 있었는지 체크하는 전역 플래그
has_input_in_current_second = False

def on_move(x, y):
    global has_input_in_current_second
    has_input_in_current_second = True

def on_click(x, y, button, pressed):
    global has_input_in_current_second
    has_input_in_current_second = True

def on_press(key):
    global has_input_in_current_second
    has_input_in_current_second = True

class FloatingTimer(QWidget):
    def __init__(self):
        super().__init__()
        self.seconds_elapsed = 0
        self.always_on_top = True  # 항상 위 고정 상태 플래그
        self.font_point_size = 36  # 기본 글자 크기
        self.bg_opacity = 180      # 기본 배경 투명도 (0~255)
        self.initUI()

        # 타이머 설정 (1초마다 실행)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)

        # 입력 리스너 백그라운드 스레드 시작
        self.mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=lambda *args: None)
        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def initUI(self):
        # 💡 Mac에서 다른 앱 클릭 시 창이 숨겨지는 현상을 막기 위해 Tool 속성 제거
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # --- 프로그램 창 아이콘 적용 ---
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel("00:00:00", self)
        self.apply_font_style()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.adjustSize()
        self.move(100, 100)

    def apply_font_style(self):
        self.label.setFont(QFont("Arial", self.font_point_size, QFont.Weight.Bold))
        self.label.setStyleSheet(
            f"color: #FFCDD0; "                               # 분홍색 텍스트
            f"background-color: rgba(0, 0, 0, {self.bg_opacity}); " # 투명도 조절 배경
            f"padding: 10px; "                                  # 안쪽 여백
            "border-radius: 8px;"                               # 둥근 모서리
        )
        self.adjustSize()

    def set_font_size(self, size):
        self.font_point_size = max(16, min(size, 80))
        self.apply_font_style()

    def set_opacity(self, opacity):
        self.bg_opacity = max(40, min(opacity, 255))
        self.apply_font_style()

    def reset_timer(self):
        self.seconds_elapsed = 0
        self.label.setText("00:00:00")
        self.adjustSize()

    # --- 마우스 휠로 크기 조절 (메인 기능) ---
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.set_font_size(self.font_point_size + 4) # 휠 올리면 확대
        else:
            self.set_font_size(self.font_point_size - 4) # 휠 내리면 축소
        event.accept()

    # --- 마우스 드래그 이동 기능 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragPosition = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.dragPosition)
            event.accept()

    # --- 우클릭 메뉴 기능 ---
    def contextMenuEvent(self, event):
        menu = QMenu(self)

        # 항상 위 고정 토글
        top_text = "항상 위 고정 해제" if self.always_on_top else "항상 위 고정"
        action_top = QAction(top_text, self)
        action_top.triggered.connect(self.toggle_always_on_top)
        menu.addAction(action_top)

        # 시간 초기화
        action_reset = QAction("시간 초기화 (00:00:00)", self)
        action_reset.triggered.connect(self.reset_timer)
        menu.addAction(action_reset)

        menu.addSeparator()

        # 배경 투명도 조절 서브메뉴
        opacity_menu = menu.addMenu("배경 투명도 조절")
        opacities = [
            ("아주 연하게 (투명)", 80),
            ("연하게", 140),
            ("보통 (기본)", 180),
            ("진하게", 220)
        ]
        for text, op in opacities:
            act = QAction(text, self)
            act.triggered.connect(lambda checked, o=op: self.set_opacity(o))
            opacity_menu.addAction(act)

        menu.addSeparator()

        # 종료
        action_close = QAction("닫기", self)
        action_close.triggered.connect(self.close)
        menu.addAction(action_close)

        menu.exec(event.globalPos())

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.update_window_flags()

    def update_window_flags(self):
        # 💡 여기에서도 Tool 속성 제거 반영
        flags = Qt.WindowType.FramelessWindowHint
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        
        self.setWindowFlags(flags)
        self.show()

    # --- 로직: 클립스튜디오 활성화 및 입력 감지 ---
    def is_clip_studio_active(self):
        try:
            active_window = gw.getActiveWindow()
            if active_window and "CLIP STUDIO PAINT" in active_window.title.upper():
                return True
        except Exception:
            pass
        return False

    def update_timer(self):
        global has_input_in_current_second

        is_csp = self.is_clip_studio_active()

        if is_csp and has_input_in_current_second:
            self.seconds_elapsed += 1

        has_input_in_current_second = False

        hrs = self.seconds_elapsed // 3600
        mins = (self.seconds_elapsed % 3600) // 60
        secs = self.seconds_elapsed % 60
        self.label.setText(f"{hrs:02d}:{mins:02d}:{secs:02d}")

    def closeEvent(self, event):
        self.mouse_listener.stop()
        self.keyboard_listener.stop()
        event.accept()

if __name__ == "__main__":
    if sys.platform == 'win32':
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
            
    app = QApplication(sys.argv)
    ex = FloatingTimer()
    ex.show()
    sys.exit(app.exec())