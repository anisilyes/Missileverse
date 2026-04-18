[app]
title = Air Defense Warfare
package.name = airdefensewarfare
package.domain = org.airdefense

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
source.include_patterns = missile.png,interceptor.png

version = 1.0.0

# Lean dependency list — no numpy, no pillow
requirements = python3,kivy==2.3.0,requests

orientation = landscape
fullscreen = 1

android.permissions = INTERNET
android.api = 33
android.minapi = 26
android.ndk = 25b
android.sdk = 33
android.archs = arm64-v8a

# Strip unused Kivy modules to shrink APK
android.add_compile_options = "sourceCompatibility = JavaVersion.VERSION_17", "targetCompatibility = JavaVersion.VERSION_17"

# Exclude heavy kivy modules we don't use
p4a.branch = master

# Only include what we actually use from kivy
kivy.modules =

android.allow_backup = False
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1
