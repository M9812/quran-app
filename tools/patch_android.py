"""تنظیمات لازم اندروید برای نوتیفیکیشن را روی پروژه Flutter اعمال می‌کند.
از داخل پوشه پروژه Flutter اجرا شود."""
import os
import re

DESUGAR = "com.android.tools:desugar_jdk_libs:2.0.4"
kts = "android/app/build.gradle.kts"
groovy = "android/app/build.gradle"

if os.path.exists(kts):
    t = open(kts, encoding="utf-8").read()
    if "isCoreLibraryDesugaringEnabled" not in t:
        t = re.sub(r"compileOptions\s*\{", "compileOptions {\n        isCoreLibraryDesugaringEnabled = true", t, count=1)
    if "coreLibraryDesugaring(" not in t:
        line = '    coreLibraryDesugaring("%s")' % DESUGAR
        if re.search(r"^dependencies\s*\{", t, re.M):
            t = re.sub(r"^dependencies\s*\{", "dependencies {\n" + line, t, count=1, flags=re.M)
        else:
            t += "\ndependencies {\n" + line + "\n}\n"
    open(kts, "w", encoding="utf-8").write(t)
elif os.path.exists(groovy):
    t = open(groovy, encoding="utf-8").read()
    if "coreLibraryDesugaringEnabled" not in t:
        t = re.sub(r"compileOptions\s*\{", "compileOptions {\n        coreLibraryDesugaringEnabled true", t, count=1)
    if "coreLibraryDesugaring '" not in t:
        line = "    coreLibraryDesugaring '%s'" % DESUGAR
        if re.search(r"^dependencies\s*\{", t, re.M):
            t = re.sub(r"^dependencies\s*\{", "dependencies {\n" + line, t, count=1, flags=re.M)
        else:
            t += "\ndependencies {\n" + line + "\n}\n"
    open(groovy, "w", encoding="utf-8").write(t)

mf = "android/app/src/main/AndroidManifest.xml"
t = open(mf, encoding="utf-8").read()
if "POST_NOTIFICATIONS" not in t:
    perms = """    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
    <uses-permission android:name="android.permission.VIBRATE"/>
    """
    t = t.replace("<application", perms + "<application", 1)
    recv = """    <receiver android:exported="false" android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationReceiver" />
        <receiver android:exported="false" android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationBootReceiver">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED"/>
                <action android:name="android.intent.action.MY_PACKAGE_REPLACED"/>
                <action android:name="android.intent.action.QUICKBOOT_POWERON"/>
                <action android:name="com.htc.intent.action.QUICKBOOT_POWERON"/>
            </intent-filter>
        </receiver>
    """
    t = t.replace("</application>", recv + "</application>", 1)
    open(mf, "w", encoding="utf-8").write(t)

print("Android patched OK")
