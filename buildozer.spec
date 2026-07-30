[app]
title = 电话
package.name = familycall
package.domain = org.example
source.dir = .
source.include_exts = py,png
version = 1.0

requirements = python3==3.10.12, kivy==2.2.1, pyjnius==1.5.0

orientation = portrait
fullscreen = 0
android.icon = icon.png
android.archs = arm64-v8a
android.api = 31
android.ndk = 25b
android.minapi = 21

android.permissions = CALL_PHONE, READ_PHONE_STATE, MODIFY_AUDIO_SETTINGS, ANSWER_PHONE_CALLS, SYSTEM_ALERT_WINDOW

android.hide_status_bar = 1
log_level = 2
