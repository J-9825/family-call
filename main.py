from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
import webbrowser
import os

# ====================== 【唯一修改区域】 ======================
REAL_PHONE = "19112685392"   # 实际拨通的真实固定号码
RING_WAIT = 11               # 模拟振铃等待秒数
APP_TITLE = "电话"           # APP名称
# ============================================================

# 固定竖屏显示
Window.orientation = 'portrait'

# 加载振铃音效（与main.py同目录，命名 ring.wav）
sound_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ring.wav")
ring_sound = SoundLoader.load(sound_path)
if ring_sound:
    ring_sound.loop = True


# ========== 拨号盘页面 ==========
class DialScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.phone_input = ""

        root = BoxLayout(orientation='vertical', padding=30, spacing=15)

        # 号码显示栏
        self.num_show = Label(
            text="", font_size=52, size_hint_y=0.2,
            color=(0, 0, 0, 1), halign='center'
        )
        root.add_widget(self.num_show)

        # 12键拨号盘
        dial_grid = GridLayout(cols=3, spacing=18, size_hint_y=0.55)
        keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']
        for k in keys:
            btn = Button(
                text=k, font_size=40,
                background_color=(0.96, 0.96, 0.96, 1),
                color=(0, 0, 0, 1)
            )
            btn.bind(on_press=self.on_key_press)
            dial_grid.add_widget(btn)
        root.add_widget(dial_grid)

        # 底部：删除 + 拨打
        bottom = BoxLayout(spacing=40, size_hint_y=0.25, padding=[40, 10, 40, 10])

        del_btn = Button(
            text="删除", font_size=24,
            background_color=(0.85, 0.85, 0.85, 1),
            color=(0, 0, 0, 1)
        )
        del_btn.bind(on_press=self.on_delete)

        call_btn = Button(
            text="拨打", font_size=30,
            background_color=(0, 0.75, 0.25, 1),
            color=(1, 1, 1, 1)
        )
        call_btn.bind(on_press=self.start_call)

        bottom.add_widget(del_btn)
        bottom.add_widget(call_btn)
        root.add_widget(bottom)

        self.add_widget(root)

    def on_key_press(self, btn):
        if len(self.phone_input) < 15:
            self.phone_input += btn.text
            self.num_show.text = self.phone_input

    def on_delete(self, btn):
        self.phone_input = self.phone_input[:-1]
        self.num_show.text = self.phone_input

    def start_call(self, btn):
        # 把输入的号码传给通话界面（只用于显示，不用于真实拨号）
        display_num = self.phone_input if self.phone_input else "未知号码"
        call_screen = self.manager.get_screen('call')
        call_screen.display_number = display_num
        self.manager.current = 'call'


# ========== 仿真通话页面 ==========
class CallScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.display_number = ""
        self.count_down = RING_WAIT
        self.is_running = False

        # 深色背景布局
        self.root_layout = BoxLayout(
            orientation='vertical', padding=40, spacing=20
        )
        with self.root_layout.canvas.before:
            Color(0.05, 0.05, 0.05, 1)
            self.bg_rect = Rectangle(pos=self.root_layout.pos, size=self.root_layout.size)
        self.root_layout.bind(pos=self._update_bg, size=self._update_bg)

        # 显示号码（显示用户输入的号，不显示真实号）
        self.num_label = Label(
            text="", font_size=44, color=(1, 1, 1, 1),
            size_hint_y=0.2, halign='center'
        )
        self.root_layout.add_widget(self.num_label)

        # 呼叫状态
        self.status_label = Label(
            text="正在呼叫...", font_size=22,
            color=(0.7, 0.7, 0.7, 1)
        )
        self.root_layout.add_widget(self.status_label)

        # 占位撑开
        self.root_layout.add_widget(Label(size_hint_y=0.4))

        # 挂断按钮
        hang_btn = Button(
            text="挂断", font_size=26, size_hint=(0.5, 0.15),
            pos_hint={'center_x': 0.5},
            background_color=(0.9, 0, 0, 1),
            color=(1, 1, 1, 1)
        )
        hang_btn.bind(on_press=self.hang_up)
        self.root_layout.add_widget(hang_btn)

        self.add_widget(self.root_layout)

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def on_enter(self):
        # 进入页面初始化
        self.count_down = RING_WAIT
        self.is_running = True
        self.num_label.text = self.display_number
        self.status_label.text = f"正在呼叫... {self.count_down}s"

        if ring_sound:
            ring_sound.play()

        # 启动倒计时
        self.timer = Clock.schedule_interval(self._tick, 1)

    def _tick(self, dt):
        self.count_down -= 1
        self.status_label.text = f"正在呼叫... {self.count_down}s"
        if self.count_down <= 0:
            self._trigger_real_call()
            return False

    def _trigger_real_call(self):
        """后台拨打真实预设号码"""
        self._stop_all()
        webbrowser.open(f"tel:{REAL_PHONE}")

    def hang_up(self, btn):
        self._stop_all()
        self.manager.current = 'dial'

    def _stop_all(self):
        self.is_running = False
        if hasattr(self, 'timer'):
            self.timer.cancel()
        if ring_sound:
            ring_sound.stop()

    def on_leave(self):
        self._stop_all()


# ========== 主程序 ==========
class CallSimApp(App):
    def build(self):
        self.title = APP_TITLE
        sm = ScreenManager()
        sm.add_widget(DialScreen(name='dial'))
        sm.add_widget(CallScreen(name='call'))
        return sm


if __name__ == "__main__":
    CallSimApp().run()