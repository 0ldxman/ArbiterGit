import arrow
from num2words import num2words
import dateparser
import calendar


class TimeManager:
    def __init__(self):
        self.time = arrow

    def today(self):
        return self.time.now().date()

    def tomorrow(self, with_time: bool = False):
        tomorrow_date = self.date_after(days=1)
        if with_time:
            tomorrow_time = self.current_time()
            return f"{tomorrow_date} {tomorrow_time}"
        else:
            return tomorrow_date

    def yesterday(self, with_time: bool = False):
        yesterday_date = self.date_after(days=-1)
        if with_time:
            yesterday_time = self.current_time()
            return f"{yesterday_date} {yesterday_time}"
        else:
            return yesterday_date

    def current_time(self):
        return self.time.now().format('HH:mm')

    def get_string_timestamp(self, date: str):
        last_date = self.get_date(date)
        spended_days = self.today() - last_date

        if spended_days.days == 0:
            return 'Сегодня'
        elif spended_days.days == 1:
            return 'Вчера'
        elif spended_days.days == 2:
            return 'Позавчера'
        elif spended_days.days > 2:
            return f'{spended_days.days} дней назад'
        elif spended_days.days < 0:
            return f'через {spended_days.days} дней'


    def get_date(self, date:str):
        return self.time.get(date, 'YYYY-MM-DD').date()

    def get_time(self, time:str):
        return self.time.get(time, 'HH:mm')

    def date_after(self, years: int = 0, months: int = 0, days: int = 0, date: str = None):
        if date:
            return self.time.get(date, 'YYYY-MM-DD').shift(years=years, months=months, days=days).date()
        else:
            return self.time.now('local').shift(years=years, months=months, days=days).to('local').date()

    def time_after(self, hours: int = 0, minutes: int = 0, time: str = None, ):
        if time:
            return arrow.get(time, 'HH:mm').shift(hours=hours, minutes=minutes).to('local').format('HH:mm')
        else:
            return self.time.now().shift(hours=hours, minutes=minutes).to('local').format('HH:mm')

    def time_difference(self, start_time: str, end_time: str, format: str = 'HH:mm'):
        start = arrow.get(start_time, format)
        end = arrow.get(end_time, format)
        return (end - start).total_seconds() / 3600

    def date_difference(self, start_date: str, end_date: str, format: str = 'YYYY-MM-DD'):
        start = self.time.get(start_date, format)
        end = self.time.get(end_date, format)
        return (end - start).days

    def format_time(self, time: str, input_format: str, output_format: str):
        return self.time.get(time, input_format).format(output_format)

    def get_calendar_info(self, year: int, month: int):
        localization = calendar.LocaleTextCalendar(locale='ru_RU')
        cal = localization.monthdayscalendar(year, month)
        header = localization.formatmonthname(year, month, width=0, withyear=True) + '\n'
        weekdays = 'Пн Вт Ср Чт Пт Сб Вс\n'
        month_str = header + weekdays

        for week in cal:
            week_str = ' '.join(f'{day or " ":>2}' for day in week) + '\n'
            month_str += week_str

        return month_str

    def convert_timezone(self, time: str, to_timezone: str, format: str = 'HH:mm'):
        return self.time.get(time, format).to(to_timezone).format(format)

    def get_day_of_week(self, years: int = 0, months: int = 0, days: int = 0, date: str = None):
        date = date if date else self.date_after(years=years, months=months, days=days)
        print(date)
        return self.time.get(date).format('dddd', locale='ru').capitalize()

    def parse_datetime(self, year=None, month=None, day=None, hour=None, minute=None, *, date=None, time=None):
        current_time = self.time.now()

        if date:
            if time:
                return self.time.get(f"{date} {time}", "YYYY-MM-DD HH:mm")
            else:
                return self.time.get(date)
        elif time:
            return arrow.get(time)
        else:
            datetime_args = {
                'year': year if year else current_time.year,
                'month': month if month else current_time.month,
                'day': day if day else current_time.day,
                'hour': hour if hour else current_time.hour,
                'minute': minute if minute else current_time.minute
            }

            return arrow.get(**datetime_args)

    def get_current_time_condition(self):
        now = self.current_time()
        hours, minutes = now.split(':')
        hours = int(hours)

        if 4 <= hours < 10:
            return 'Morning'
        elif 10 <= hours < 16:
            return 'Day'
        elif 16 <= hours < 22:
            return 'Evening'
        else:
            return 'Night'



class TaskManager(TimeManager):
    def __init__(self):
        super().__init__()
        self.tasks = []

    def add_task(self, task_name: str, due_date, due_time=None):
        if due_time:
            due_datetime = self.parse_datetime(time=due_time, date=due_date)
        else:
            due_datetime = self.parse_datetime(time=due_date)
        self.tasks.append({'name': task_name, 'due_datetime': due_datetime})

    def remove_task(self, task_name):
        self.tasks = [task for task in self.tasks if task['name'] != task_name]

    def list_tasks(self):
        for idx, task in enumerate(self.tasks, start=1):
            print(f"{idx}. {task['name']} - Due: {task['due_datetime'].format('YYYY-MM-DD HH:mm')}")