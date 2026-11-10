# راه‌اندازی پروژه در VS Code

## ۰) پیش‌نیازها
1. نصب Flutter SDK: https://docs.flutter.dev/get-started/install
2. نصب Android Studio (برای SDK و شبیه‌ساز اندروید) و ساخت یک Android Emulator
3. در VS Code افزونه‌های **Flutter** و **Dart** را نصب کنید
4. در ترمینال اجرا کنید: `flutter doctor` و مشکلات را رفع کنید

## ۱) ساخت پروژه
```bash
flutter create quran_notifier
cd quran_notifier
```
سپس:
- فایل `pubspec.yaml` پروژه را با فایل همراه این پیام جایگزین کنید
- فایل `lib/main.dart` را با فایل همراه جایگزین کنید
- پوشه `assets` بسازید و فایل `quran_data.json` (خروجی اسکریپت پایتون قبلی) را با نام **`assets/quran.json`** داخلش بگذارید

```bash
flutter pub get
```

## ۲) تنظیم اندروید (ضروری برای نوتیفیکیشن)

### الف) فایل `android/app/build.gradle.kts`
داخل بلاک `compileOptions` این دو خط را اضافه/تغییر دهید:
```kotlin
compileOptions {
    isCoreLibraryDesugaringEnabled = true
    sourceCompatibility = JavaVersion.VERSION_11
    targetCompatibility = JavaVersion.VERSION_11
}
```
و در انتهای فایل (اگر `dependencies` ندارد، بسازید):
```kotlin
dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.4")
}
```
(اگر فایل شما `build.gradle` با سینتکس Groovy است: `coreLibraryDesugaringEnabled true` و `coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.0.4'`)

### ب) فایل `android/app/src/main/AndroidManifest.xml`
بالای تگ `<application>` (داخل `<manifest>`):
```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
<uses-permission android:name="android.permission.VIBRATE"/>
```
و داخل تگ `<application>` (کنار `<activity>`):
```xml
<receiver android:exported="false"
    android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationReceiver" />
<receiver android:exported="false"
    android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationBootReceiver">
    <intent-filter>
        <action android:name="android.intent.action.BOOT_COMPLETED"/>
        <action android:name="android.intent.action.MY_PACKAGE_REPLACED"/>
        <action android:name="android.intent.action.QUICKBOOT_POWERON" />
        <action android:name="com.htc.intent.action.QUICKBOOT_POWERON"/>
    </intent-filter>
</receiver>
```

## ۳) اجرا
۱. شبیه‌ساز اندروید را روشن کنید (یا گوشی را با USB و USB debugging وصل کنید)
۲. در VS Code کلید `F5` یا دستور `flutter run`
۳. اولین بار اجازه نوتیفیکیشن را قبول کنید
۴. در «تنظیمات» عدد `1` دقیقه را بزنید، سوئیچ را روشن و ذخیره کنید؛ بعد از یک دقیقه اولین آیه می‌آید
   (یا دکمه تست را بزنید)

## ۴) ساخت APK برای نصب روی گوشی
```bash
flutter build apk --release
```
خروجی: `build/app/outputs/flutter-apk/app-release.apk`

## نکات مهم
- هر بار که برنامه باز شود، ۲۰۰ نوتیفیکیشن بعدی دوباره زمان‌بندی می‌شود. با فاصله ۶۰ دقیقه حدود ۸ روز پوشش دارد؛ با فاصله ۱ دقیقه فقط ~۳ ساعت.
- نوتیفیکیشن‌ها «تقریبی» هستند و ممکن است در حالت Doze چند دقیقه دیر برسند. برای زمان دقیق، مجوز SCHEDULE_EXACT_ALARM و حالت `exactAllowWhileIdle` لازم است.
- بعضی گوشی‌ها (شیائومی، سامسونگ، هواوی) برنامه را در پس‌زمینه محدود می‌کنند؛ در تنظیمات گوشی، بهینه‌سازی باتری برنامه را روی «بدون محدودیت» بگذارید.
