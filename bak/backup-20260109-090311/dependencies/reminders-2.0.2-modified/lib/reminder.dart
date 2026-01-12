import 'reminders_list.dart';

class Reminder {
  RemList list;
  String? id;
  String title;
  DateTime? dueDate;
  int priority;
  bool isCompleted;
  String? notes;
  String? recurrence;  // 新增：循环类型 (yearly/monthly/weekly)

  Reminder(
      {required this.list,
      this.id,
      required this.title,
      this.dueDate,
      this.priority = 0,
      this.isCompleted = false,
      this.notes,
      this.recurrence});

  Reminder.fromJson(Map<String, dynamic> json)
      : list = RemList.fromJson(json['list']),
        id = json['id'],
        title = json['title'],
        priority = json['priority'],
        isCompleted = json['isCompleted'],
        notes = json['notes'],
        recurrence = json['recurrence'] {
    if (json['dueDate'] != null) {
      final date = json['dueDate'];
      dueDate = DateTime(date['year']!, date['month']!, date['day']!,
          date['hour'] ?? 00, date['minute'] ?? 00, date['second'] ?? 00);
    }
  }

  Map<String, dynamic> toJson() {
    final json = {
      'list': list.id,
      'id': id,
      'title': title,
      'dueDate': dueDate == null
          ? null
          : {
              'year': dueDate?.year,
              'month': dueDate?.month,
              'day': dueDate?.day,
              'hour': dueDate?.hour,
              'minute': dueDate?.minute,
              'second': dueDate?.second,
            },
      'priority': priority,
      'isCompleted': isCompleted,
      'notes': notes
    };

    // 只有当recurrence不为null时才添加
    if (recurrence != null) {
      json['recurrence'] = recurrence;
    }

    return json;
  }

  @override
  String toString() =>
      '''List: ${list.title}\tTitle: $title\tdueDate: $dueDate\tPriority: 
      $priority\tisComplete: $isCompleted\tNotes: $notes\tID: $id''';
}
