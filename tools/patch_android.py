"""
تنظیمات لازم اندروید برای نوتیفیکیشن را روی پروژه Flutter اعمال می‌کند
و در پایان بررسی می‌کند همه‌چیز واقعاً اعمال شده باشد (در غیر این صورت ساخت متوقف می‌شود).
از داخل پوشه پروژه Flutter اجرا شود.
"""
import os
import re
import sys

DESUGAR = "com.android.tools:desugar_jdk_libs:2.0.4"
KTS = "android/app/build.gradle.kts"
GROOVY = "android/app/build.gradle"
MANIFEST = "android/app/src/main/AndroidManifest.xml"


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, t):
    with open(p, "w", encoding="utf-8") as f:
        f.write(t)


# ------------------------------------------------------------------ Gradle
def patch_gradle():
    if os.path.exists(KTS):
        path, kts = KTS, True
    elif os.path.exists(GROOVY):
        path, kts = GROOVY, False
    else:
        sys.exit("ERROR: build.gradle(.kts) not found")

    t = read(path)

    if kts:
        desugar_flag = "isCoreLibraryDesugaringEnabled = true"
        desugar_re = r"isCoreLibraryDesugaringEnabled\s*=\s*true"
        dep_line = '    coreLibraryDesugaring("%s")' % DESUGAR
        dep_marker = "coreLibraryDesugaring("
        minify_off = "isMinifyEnabled = false"
        shrink_off = "isShrinkResources = false"
        minify_re_false = r"isMinifyEnabled\s*=\s*false"
        fix = [(r"isMinifyEnabled\s*=\s*true", minify_off),
               (r"isShrinkResources\s*=\s*true", shrink_off)]
        fb_compile = "\nandroid {\n    compileOptions {\n        %s\n    }\n}\n" % desugar_flag
        fb_minify = ("\nandroid {\n    buildTypes {\n        getByName(\"release\") {\n"
                     "            %s\n            %s\n        }\n    }\n}\n") % (minify_off, shrink_off)
    else:
        desugar_flag = "coreLibraryDesugaringEnabled true"
        desugar_re = r"coreLibraryDesugaringEnabled\s+true"
        dep_line = "    coreLibraryDesugaring '%s'" % DESUGAR
        dep_marker = "coreLibraryDesugaring '"
        minify_off = "minifyEnabled false"
        shrink_off = "shrinkResources false"
        minify_re_false = r"minifyEnabled\s+false"
        fix = [(r"minifyEnabled\s+true", minify_off),
               (r"shrinkResources\s+true", shrink_off)]
        fb_compile = "\nandroid {\n    compileOptions {\n        %s\n    }\n}\n" % desugar_flag
        fb_minify = ("\nandroid {\n    buildTypes {\n        release {\n"
                     "            %s\n            %s\n        }\n    }\n}\n") % (minify_off, shrink_off)

    # 1) desugaring (لازم برای flutter_local_notifications)
    if not re.search(desugar_re, t):
        t, n = re.subn(r"compileOptions\s*\{", "compileOptions {\n        " + desugar_flag, t, count=1)
        if n == 0:
            t += fb_compile
    if dep_marker not in t:
        if re.search(r"^dependencies\s*\{", t, re.M):
            t = re.sub(r"^dependencies\s*\{", "dependencies {\n" + dep_line, t, count=1, flags=re.M)
        else:
            t += "\ndependencies {\n" + dep_line + "\n}\n"

    # 2) خاموش کردن R8 (علت خطای "Missing type parameter" در نسخه release)
    for pat, rep in fix:
        t = re.sub(pat, rep, t)
    if not re.search(minify_re_false, t):
        t, n = re.subn(
            r"(buildTypes\s*\{\s*release\s*\{)",
            lambda m: m.group(1) + "\n            " + minify_off + "\n            " + shrink_off,
            t, count=1)
        if n == 0:
            t += fb_minify

    write(path, t)

    # بررسی نهایی
    t = read(path)
    ok = (re.search(desugar_re, t) and dep_marker in t and re.search(minify_re_false, t))
    if not ok:
        sys.exit("ERROR: gradle patch verification failed")
    print("Gradle patched OK:", path)


# ---------------------------------------------------------------- Manifest
def patch_manifest():
    t = read(MANIFEST)

    if "POST_NOTIFICATIONS" not in t:
        perms = (
            '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>\n'
            '    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>\n'
            '    <uses-permission android:name="android.permission.VIBRATE"/>\n'
            '    <uses-permission android:name="android.permission.USE_EXACT_ALARM"/>\n'
            '    <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" android:maxSdkVersion="32"/>\n'
            "    "
        )
        t = t.replace("<application", perms + "<application", 1)

    if "ScheduledNotificationReceiver" not in t:
        recv = (
            '    <receiver android:exported="false" android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationReceiver" />\n'
            '        <receiver android:exported="false" android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationBootReceiver">\n'
            "            <intent-filter>\n"
            '                <action android:name="android.intent.action.BOOT_COMPLETED"/>\n'
            '                <action android:name="android.intent.action.MY_PACKAGE_REPLACED"/>\n'
            '                <action android:name="android.intent.action.QUICKBOOT_POWERON"/>\n'
            '                <action android:name="com.htc.intent.action.QUICKBOOT_POWERON"/>\n'
            "            </intent-filter>\n"
            "        </receiver>\n"
            "    "
        )
        t = t.replace("</application>", recv + "</application>", 1)

    write(MANIFEST, t)

    t = read(MANIFEST)
    needed = ["POST_NOTIFICATIONS", "USE_EXACT_ALARM", "RECEIVE_BOOT_COMPLETED",
              "ScheduledNotificationReceiver", "ScheduledNotificationBootReceiver"]
    missing = [k for k in needed if k not in t]
    if missing:
        sys.exit("ERROR: manifest patch verification failed: %s" % missing)
    print("Manifest patched OK")


PROGUARD = """-keepattributes Signature
-keepattributes *Annotation*
-keep class com.google.gson.reflect.TypeToken { *; }
-keep class * extends com.google.gson.reflect.TypeToken
-keep class com.dexterous.** { *; }
"""


def patch_proguard():
    """قانون‌های نگه‌داری برای Gson (در صورت فعال بودن R8 هم خطای Missing type parameter نیاید)."""
    write("android/app/proguard-rules.pro", PROGUARD)
    path = KTS if os.path.exists(KTS) else GROOVY
    t = read(path)
    if "proguard-rules.pro" in t:
        return
    line = 'proguardFiles("proguard-rules.pro")' if path == KTS else "proguardFiles 'proguard-rules.pro'"
    t, n = re.subn(
        r"(buildTypes\s*\{\s*release\s*\{)",
        lambda m: m.group(1) + "\n            " + line,
        t, count=1)
    if n:
        write(path, t)
    print("Proguard rules added")


def patch_gradle_properties():
    """R8 full mode علت اصلی خطای Missing type parameter است؛ خاموشش می‌کنیم."""
    path = "android/gradle.properties"
    t = read(path) if os.path.exists(path) else ""
    if "android.enableR8.fullMode" not in t:
        if t and not t.endswith("\n"):
            t += "\n"
        t += "android.enableR8.fullMode=false\n"
        write(path, t)
    print("gradle.properties OK")


patch_gradle()
patch_manifest()
patch_proguard()
patch_gradle_properties()
print("Android patched OK")
