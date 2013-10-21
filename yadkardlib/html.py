#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''This module contains html body of application and its predefined resposes'''

class ResposeObj():
    def __init__(self, ref, cite, error):
        self.ref = ref
        self.cite = cite
        self.error = error

skeleton = """
<html dir="rtl">
<head>
 <title>یادکرد</title>
</head>
<body style="font-family: tahoma; font-size:0.8em">
 <form method="get" action="yadkard.fcgi">
  <p>
   نشانی وب:<br><input type="text" size="100" name="url">
  <input type="submit" value="یادکرد">
  </p>
 </form>
  <p>
   پانویس کوتاه‌شده و یادکرد:<br>
   <textarea rows="13" cols="80" readonly>%s\n\n%s</textarea>
  </p>
  <p>
   احتمال خطا در تشخیص زبان: %s ٪
  </p>
</body>
</html>"""

default_response = (
    'این ابزار برای تولید یادکرد مناسب ویکی‌پدیای فارسی، برابر شیوه‌نامهٔ شیکاگو، کاربرد \
دارد.',
    'هم‌اکنون از وب‌گاه‌های زیر پشتیبانی می‌شود:\n\
* http://books.google.com (گوگل بوکس)\n\
* http://www.noormags.com (نورمگز)\n\
* http://www.noorlib.ir (کتابخانه دیجیتال نور)\n\
http://www.adinebook.com (آدینه‌بوک)\n\
* http://dx.doi.org (یا متنی که شامل «شناسانۀ برنمود رقمی» (doi) باشد)\n\
* شابک (ISBN) برای بیشتر کتاب‌ها (ایرانی و خارجی)\n\n\
در صورت بروز مشکل یا درست عمل نکردن ابزار می‌توانید با من (دالبا) تماس \
بگیرید\n\
امکان گسترش ابزار برای کتابخانه‌های دیجیتالی که خروجی Bibtex یا \
RefMan ‏(RIS) تولید می‌کنند وجود دارد.',
    '??')

undefined_url_response = ('نشانی واردشده برای این ابزار تعریف نشده‌است.',
                      'اگر کتابخانهٔ دیجیتالی می‌شناسید که خروجی \
bibtex یا RIS تولید می‌کند، لطفاً موضوع را با توسعه‌دهنده ٔ ابزار در میان بگذارید\
 تا در صورت امکان به ابزار افزوده شود.',
                      '۱۰۰')

httperror_response = ('خطای اچ‌تی‌تی‌پی در دریافت اطلاعات.',
                      'اطلاعات قابل دسترس نبودند.',
                      '۱۰۰')

other_exception_response = ('خطای پیش‌بینی‌نشده‌ای رخ داد.',
                      'لطفاً مطمئن شوید که نشانی وب را درست وارد کرده‌اید.',
                      '۱۰۰')