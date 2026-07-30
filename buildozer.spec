[app]
title = 电话
package.name = familycall
package.domain = org.example
source.dir = .
source.include_exts = py,png
version = 1.0

requirements = python3, kivy, pyjnius

orientation = portrait
fullscreen = 0
android.icon = icon.png
android.archs = arm64-v8a, armeabi-v7a
android.api = 33
android.ndk = 25b
android.minapi = 21

# 全部所需权限
android.permissions = CALL_PHONE, READ_PHONE_STATE, MODIFY_AUDIO_SETTINGS, ANSWER_PHONE_CALLS, SYSTEM_ALERT_WINDOW

android.hide_status_bar = 1
