import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

// ====================== مدل داده ======================

class Ayah {
  final int surahNo;
  final String surah;
  final int no;
  final String ar;
  final String fa;
  Ayah(this.surahNo, this.surah, this.no, this.ar, this.fa);

  factory Ayah.fromJson(Map<String, dynamic> j) {
    final surahNo = j['surah_number'] as int;
    final no = j['number'] as int;
    var ar = j['arabic'] as String;
    // API بسم‌الله را به اول آیه ۱ هر سوره می‌چسباند؛ آن را جدا می‌کنیم.
    if (no == 1 && surahNo != 1 && ar.startsWith('بِسْمِ')) {
      final w = ar.split(' ');
      if (w.length > 4) ar = w.skip(4).join(' ');
    }
    return Ayah(surahNo, j['surah'] as String, no, ar, j['fa'] as String);
  }
}

late List<Ayah> allAyahs;

// ====================== تنظیمات ======================

class Settings {
  bool enabled;
  int minutes;
  bool random;
  int startMs; // لحظه شروع برنامه نوتیفیکیشن‌ها
  int startIndex; // اندیس آیه‌ای که از آن شروع شده

  Settings({
    this.enabled = false,
    this.minutes = 60,
    this.random = true,
    this.startMs = 0,
    this.startIndex = 0,
  });

  static Future<Settings> load() async {
    final p = await SharedPreferences.getInstance();
    return Settings(
      enabled: p.getBool('enabled') ?? false,
      minutes: p.getInt('minutes') ?? 60,
      random: p.getBool('random') ?? true,
      startMs: p.getInt('startMs') ?? 0,
      startIndex: p.getInt('startIndex') ?? 0,
    );
  }

  Future<void> save() async {
    final p = await SharedPreferences.getInstance();
    await p.setBool('enabled', enabled);
    await p.setInt('minutes', minutes);
    await p.setBool('random', random);
    await p.setInt('startMs', startMs);
    await p.setInt('startIndex', startIndex);
  }
}

// ====================== نوتیفیکیشن ======================

class Notifier {
  static final _plugin = FlutterLocalNotificationsPlugin();

  // تعداد نوتیفیکیشن‌هایی که از قبل زمان‌بندی می‌شود (کم نگه داشته شده تا برنامه کند نشود)
  static const batchSize = 60;

  static Future<void>? _initFuture;
  static Future<void> init() => _initFuture ??= _init();

  static Future<void> _init() async {
    tzdata.initializeTimeZones();
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    await _plugin.initialize(const InitializationSettings(android: android));
    await _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
  }

  static NotificationDetails _details(String body) => NotificationDetails(
        android: AndroidNotificationDetails(
          'quran_channel',
          'آیات قرآن',
          channelDescription: 'یادآوری آیات قرآن همراه ترجمه',
          importance: Importance.high,
          priority: Priority.high,
          styleInformation: BigTextStyleInformation(body), // نمایش کامل آیه
        ),
      );

  static String _title(Ayah a) => '${a.surah} - آیه ${a.no}';
  static String _body(Ayah a) => '${a.ar}\n\n${a.fa}';

  static Future<void> showNow(Settings s) async {
    await init();
    final a = s.random
        ? allAyahs[Random().nextInt(allAyahs.length)]
        : allAyahs[s.startIndex % allAyahs.length];
    await _plugin.show(9999, _title(a), _body(a), _details(_body(a)));
  }

  static Future<void> _zoned(int id, Ayah a, DateTime when) async {
    final details = _details(_body(a));
    final date = tz.TZDateTime.from(when, tz.UTC);
    try {
      // آلارم دقیق (برای رسیدن به‌موقع در گوشی‌هایی مثل شیائومی)
      await _plugin.zonedSchedule(
        id,
        _title(a),
        _body(a),
        date,
        details,
        androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
        uiLocalNotificationDateInterpretation:
            UILocalNotificationDateInterpretation.absoluteTime,
      );
    } catch (_) {
      // اگر اجازه آلارم دقیق نبود، حالت تقریبی
      await _plugin.zonedSchedule(
        id,
        _title(a),
        _body(a),
        date,
        details,
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        uiLocalNotificationDateInterpretation:
            UILocalNotificationDateInterpretation.absoluteTime,
      );
    }
  }

  /// نوتیفیکیشن‌های آینده را زمان‌بندی می‌کند.
  /// force=false: فقط وقتی تعداد باقی‌مانده کم شده باشد دوباره می‌سازد.
  static Future<void> reschedule(Settings s, {bool force = false}) async {
    await init();

    if (!s.enabled || s.startMs == 0) {
      await _plugin.cancelAll();
      return;
    }

    if (!force) {
      final pending = await _plugin.pendingNotificationRequests();
      if (pending.length >= batchSize ~/ 2) return;
    }

    await _plugin.cancelAll();

    final start = DateTime.fromMillisecondsSinceEpoch(s.startMs);
    final intervalMs = s.minutes * 60 * 1000;
    final elapsed = DateTime.now().difference(start).inMilliseconds;
    final first = elapsed ~/ intervalMs + 1; // اولین نوبتِ هنوز نیامده

    for (var i = 0; i < batchSize; i++) {
      final n = first + i;
      final when = start.add(Duration(minutes: s.minutes * n));
      final idx = s.random
          ? Random(s.startMs + n).nextInt(allAyahs.length)
          : (s.startIndex + n - 1) % allAyahs.length;
      await _zoned(i, allAyahs[idx], when);
    }
  }
}

// ====================== برنامه ======================

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final raw = await rootBundle.loadString('assets/quran.json');
  allAyahs = (jsonDecode(raw) as List)
      .map((e) => Ayah.fromJson(e as Map<String, dynamic>))
      .toList();

  runApp(const QuranApp());

  // بعد از نمایش برنامه، بدون انتظار و بدون اینکه خطا برنامه را بخواباند
  _setupNotifications();
}

Future<void> _setupNotifications() async {
  try {
    await Notifier.init();
    await Notifier.reschedule(await Settings.load());
  } catch (e) {
    debugPrint('notification setup error: $e');
  }
}

class QuranApp extends StatelessWidget {
  const QuranApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'قرآن',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: Colors.green, useMaterial3: true),
      builder: (context, child) =>
          Directionality(textDirection: TextDirection.rtl, child: child!),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _page = 0;

  @override
  Widget build(BuildContext context) {
    final titles = ['فهرست قرآن', 'تنظیمات'];
    return Scaffold(
      appBar: AppBar(title: Text(titles[_page])),
      drawer: Drawer(
        child: ListView(
          children: [
            const DrawerHeader(
              child: Center(
                child: Text('قرآن کریم', style: TextStyle(fontSize: 28)),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.menu_book),
              title: const Text('فهرست قرآن'),
              selected: _page == 0,
              onTap: () {
                setState(() => _page = 0);
                Navigator.pop(context);
              },
            ),
            ListTile(
              leading: const Icon(Icons.settings),
              title: const Text('تنظیمات'),
              selected: _page == 1,
              onTap: () {
                setState(() => _page = 1);
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
      body: _page == 0 ? const SurahListPage() : const SettingsPage(),
    );
  }
}

// ---------- فهرست سوره‌ها ----------

class SurahListPage extends StatelessWidget {
  const SurahListPage({super.key});

  @override
  Widget build(BuildContext context) {
    // گروه‌بندی آیات بر اساس سوره
    final Map<int, List<Ayah>> surahs = {};
    for (final a in allAyahs) {
      surahs.putIfAbsent(a.surahNo, () => []).add(a);
    }
    final keys = surahs.keys.toList()..sort();

    return ListView.builder(
      itemCount: keys.length,
      itemBuilder: (context, i) {
        final list = surahs[keys[i]]!;
        return ListTile(
          leading: CircleAvatar(child: Text('${keys[i]}')),
          title: Text(list.first.surah, style: const TextStyle(fontSize: 20)),
          subtitle: Text('${list.length} آیه'),
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => SurahPage(ayahs: list)),
          ),
        );
      },
    );
  }
}

// ---------- صفحه یک سوره ----------

class SurahPage extends StatelessWidget {
  final List<Ayah> ayahs;
  const SurahPage({super.key, required this.ayahs});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(ayahs.first.surah)),
      body: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: ayahs.length,
        itemBuilder: (context, i) {
          final a = ayahs[i];
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('آیه ${a.no}',
                      style: TextStyle(
                          color: Theme.of(context).colorScheme.primary)),
                  const SizedBox(height: 8),
                  Text(a.ar,
                      style: const TextStyle(fontSize: 24, height: 2),
                      textAlign: TextAlign.right),
                  const Divider(),
                  Text(a.fa, style: const TextStyle(fontSize: 16, height: 1.8)),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

// ---------- تنظیمات ----------

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});
  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _ctrl = TextEditingController(text: '60');
  bool _enabled = false;
  bool _random = true;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    Settings.load().then((s) {
      setState(() {
        _enabled = s.enabled;
        _random = s.random;
        _ctrl.text = '${s.minutes}';
        _loaded = true;
      });
    });
  }

  void _snack(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  Future<void> _save() async {
    final m = int.tryParse(_ctrl.text.trim());
    if (m == null || m < 1) {
      _snack('یک عدد معتبر (حداقل ۱ دقیقه) وارد کنید');
      return;
    }
    final old = await Settings.load();
    final now = DateTime.now().millisecondsSinceEpoch;

    // ادامه از همان جایی که ترتیب آیات رسیده بود
    var startIndex = old.startIndex;
    if (old.enabled && old.startMs > 0) {
      final passed = (now - old.startMs) ~/ (old.minutes * 60 * 1000);
      startIndex = (old.startIndex + passed) % allAyahs.length;
    }

    final s = Settings(
      enabled: _enabled,
      minutes: m,
      random: _random,
      startMs: now,
      startIndex: startIndex,
    );
    await s.save();
    try {
      await Notifier.reschedule(s, force: true);
      _snack(_enabled
          ? 'ذخیره شد؛ هر $m دقیقه یک آیه می‌آید'
          : 'ذخیره شد؛ نوتیفیکیشن خاموش است');
    } catch (e) {
      _snack('خطا در زمان‌بندی: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) return const Center(child: CircularProgressIndicator());
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        SwitchListTile(
          title: const Text('ارسال نوتیفیکیشن آیه'),
          value: _enabled,
          onChanged: (v) => setState(() => _enabled = v),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _ctrl,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: 'هر چند دقیقه یک آیه؟',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [1, 15, 30, 60, 120, 360]
              .map((m) => ActionChip(
                    label: Text('$m دقیقه'),
                    onPressed: () => setState(() => _ctrl.text = '$m'),
                  ))
              .toList(),
        ),
        SwitchListTile(
          title: const Text('انتخاب تصادفی آیه'),
          subtitle: const Text('در حالت خاموش، آیات پشت سر هم و به ترتیب قرآن می‌آیند'),
          value: _random,
          onChanged: (v) => setState(() => _random = v),
        ),
        const SizedBox(height: 16),
        FilledButton(onPressed: _save, child: const Text('ذخیره تنظیمات')),
        const SizedBox(height: 8),
        OutlinedButton(
          onPressed: () async {
            try {
              final s = await Settings.load();
              await Notifier.showNow(s);
            } catch (e) {
              _snack('خطا: $e');
            }
          },
          child: const Text('تست: همین الان یک نوتیفیکیشن بفرست'),
        ),
      ],
    );
  }
}
