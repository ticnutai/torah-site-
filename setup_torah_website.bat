@echo off
chcp 65001 > nul
title 🕎 אתר התורה - התקנה אוטומטית
color 0A

echo.
echo 🚀 אתר התורה - התקנה אוטומטית מלאה
echo ============================================
echo.

REM בדיקה שאנחנו בתיקייה הנכונה
if not exist "torah.db" (
    echo ❌ שגיאה: לא נמצא קובץ torah.db
    echo ודא שאתה מריץ את הסקריפט בתיקייה torah-website
    echo עם הקובץ torah.db
    pause
    exit /b 1
)

echo ✅ נמצא קובץ torah.db
echo.

REM שלב 1: תיקון שם קובץ HTML
echo 📝 שלב 1: מתקן שמות קבצים...
if exist "index.html.html" (
    ren "index.html.html" "index.html" 2>nul
    echo ✅ תוקן שם הקובץ index.html
) else (
    if exist "index.html" (
        echo ✅ קובץ index.html כבר קיים
    ) else (
        echo ❌ לא נמצא קובץ index.html או index.html.html
        echo צריך ליצור את קובץ האתר קודם!
        pause
        exit /b 1
    )
)
echo.

REM שלב 2: יצירת סקריפט הבנייה
echo 🔧 שלב 2: יוצר סקריפט בניית הנתונים...

(
echo #!/usr/bin/env python3
echo # -*- coding: utf-8 -*-
echo """
echo בניית נתונים לאתר התורה - גרסה אוטומטית
echo """
echo.
echo import sqlite3
echo import json
echo import os
echo from datetime import datetime
echo.
echo class TorahWebsiteBuilder:
echo     def __init__^(self, db_path="torah.db", output_dir="website_data"^):
echo         self.db_path = db_path
echo         self.output_dir = output_dir
echo         self.conn = None
echo.        
echo     def connect_db^(self^):
echo         if not os.path.exists^(self.db_path^):
echo             print^(f"❌ שגיאה: הקובץ {self.db_path} לא נמצא!"^)
echo             return False
echo         self.conn = sqlite3.connect^(self.db_path^)
echo         self.conn.row_factory = sqlite3.Row
echo         print^(f"✅ מחובר ל-{self.db_path}"^)
echo         return True
echo.
echo     def setup_directories^(self^):
echo         directories = [
echo             self.output_dir,
echo             f"{self.output_dir}/books",
echo             f"{self.output_dir}/api",
echo             f"{self.output_dir}/search"
echo         ]
echo         for directory in directories:
echo             os.makedirs^(directory, exist_ok=True^)
echo             print^(f"📁 {directory}"^)
echo.
echo     def save_json^(self, data, filepath^):
echo         full_path = f"{self.output_dir}/{filepath}"
echo         with open^(full_path, 'w', encoding='utf-8'^) as f:
echo             json.dump^(data, f, ensure_ascii=False, indent=2^)
echo         return filepath
echo.
echo     def create_slug^(self, text^):
echo         hebrew_to_english = {
echo             "בראשית": "genesis", "שמות": "exodus", "ויקרא": "leviticus",
echo             "במדבר": "numbers", "דברים": "deuteronomy"
echo         }
echo         return hebrew_to_english.get^(text, text.lower^(^).replace^(" ", "-"^)^)
echo.
echo     def create_books_index^(self^):
echo         print^("\\n📚 יוצר אינדקס ספרים..."^)
echo         cursor = self.conn.cursor^(^)
echo         cursor.execute^("SELECT * FROM tbl_Sefer ORDER BY ID"^)
echo         books = [dict^(row^) for row in cursor.fetchall^(^)]
echo         books_index = {"books": []}
echo         for book in books:
echo             book_id = book["ID"]
echo             book_name = book["SeferName"]
echo             cursor.execute^("SELECT COUNT^(DISTINCT Perek^) FROM tbl_Torah WHERE Sefer = ?", ^(book_id,^)^)
echo             chapter_count = cursor.fetchone^(^)[0]
echo             cursor.execute^("SELECT COUNT^(*^) FROM tbl_Torah WHERE Sefer = ?", ^(book_id,^)^)
echo             verse_count = cursor.fetchone^(^)[0]
echo             cursor.execute^("""
echo                 SELECT COUNT^(q.ID^) FROM tbl_Question q
echo                 JOIN tbl_Title t ON q.TitleID = t.ID
echo                 JOIN tbl_Torah tor ON t.TorahID = tor.ID
echo                 WHERE tor.Sefer = ?""", ^(book_id,^)^)
echo             question_count = cursor.fetchone^(^)[0]
echo             book_info = {
echo                 "id": book_id, "name": book_name, "slug": self.create_slug^(book_name^),
echo                 "chapter_count": chapter_count, "verse_count": verse_count,
echo                 "question_count": question_count, "file_path": f"books/book_{book_id}.json"
echo             }
echo             books_index["books"].append^(book_info^)
echo             print^(f"  📖 {book_name}: {chapter_count} פרקים, {verse_count} פסוקים, {question_count} שאלות"^)
echo         self.save_json^(books_index, "api/books_index.json"^)
echo         print^("  ✅ אינדקס ספרים נשמר"^)
echo         return books_index
echo.
echo     def create_basic_book_files^(self, books_index^):
echo         print^("\\n📖 יוצר קבצי ספרים בסיסיים..."^)
echo         cursor = self.conn.cursor^(^)
echo         for book_info in books_index["books"]:
echo             book_id = book_info["id"]
echo             book_name = book_info["name"]
echo             print^(f"  📚 מעבד ספר: {book_name}"^)
echo             book_data = {"book_info": book_info, "chapters": []}
echo             cursor.execute^("SELECT DISTINCT Perek FROM tbl_Torah WHERE Sefer = ? ORDER BY Perek LIMIT 3", ^(book_id,^)^)
echo             chapters = [row[0] for row in cursor.fetchall^(^)]
echo             for chapter_num in chapters:
echo                 chapter_data = {"chapter_number": chapter_num, "verses": []}
echo                 cursor.execute^("SELECT ID, PasukNum, Pasuk FROM tbl_Torah WHERE Sefer = ? AND Perek = ? ORDER BY PasukNum LIMIT 10", ^(book_id, chapter_num^)^)
echo                 verses = cursor.fetchall^(^)
echo                 for verse in verses:
echo                     torah_id, verse_num, verse_text = verse["ID"], verse["PasukNum"], verse["Pasuk"]
echo                     cursor.execute^("SELECT COUNT^(*^) FROM tbl_Title WHERE TorahID = ?", ^(torah_id,^)^)
echo                     question_count = cursor.fetchone^(^)[0]
echo                     verse_data = {
echo                         "verse_number": verse_num, "text": verse_text, "torah_id": torah_id,
echo                         "total_questions": question_count, "question_groups": []
echo                     }
echo                     if question_count ^> 0:
echo                         verse_data["question_groups"] = [{"title": "שאלות", "questions": [f"שאלה {i+1} על פסוק {verse_num}" for i in range^(min^(3, question_count^)^)]}]
echo                     chapter_data["verses"].append^(verse_data^)
echo                 book_data["chapters"].append^(chapter_data^)
echo             self.save_json^(book_data, f"books/book_{book_id}.json"^)
echo             print^(f"    ✅ {len^(book_data['chapters']^)} פרקים נשמרו"^)
echo.
echo     def create_parshiot_data^(self^):
echo         print^("\\n📜 יוצר נתוני פרשות..."^)
echo         cursor = self.conn.cursor^(^)
echo         cursor.execute^("SELECT p.*, s.SeferName FROM tbl_Parsha p JOIN tbl_Sefer s ON p.SeferID = s.ID ORDER BY p.ID"^)
echo         parshiot = []
echo         for row in cursor.fetchall^(^):
echo             parsha_data = {
echo                 "id": row["ID"], "name": row["ParshaName"], "sefer_id": row["SeferID"],
echo                 "sefer_name": row["SeferName"], "start_chapter": row["StartPerek"],
echo                 "start_verse": row["StartPasuk"]
echo             }
echo             parshiot.append^(parsha_data^)
echo         parshiot_data = {"parshiot": parshiot, "total_count": len^(parshiot^)}
echo         self.save_json^(parshiot_data, "api/parshiot.json"^)
echo         print^(f"  ✅ {len^(parshiot^)} פרשות נשמרו"^)
echo.
echo     def create_manifest^(self^):
echo         manifest = {
echo             "version": "1.0", "created": datetime.now^(^).isoformat^(^),
echo             "description": "נתוני תורה מוכנים לאתר",
echo             "api_endpoints": {
echo                 "books_list": "api/books_index.json",
echo                 "book_content": "books/book_{id}.json", "parshiot": "api/parshiot.json"
echo             }
echo         }
echo         self.save_json^(manifest, "manifest.json"^)
echo         print^("  ✅ מניפסט נוצר"^)
echo.
echo     def build_website_data^(self^):
echo         print^("🌐 בונה נתונים לאתר התורה"^)
echo         print^("=" * 50^)
echo         try:
echo             if not self.connect_db^(^): return False
echo             self.setup_directories^(^)
echo             books_index = self.create_books_index^(^)
echo             self.create_basic_book_files^(books_index^)
echo             self.create_parshiot_data^(^)
echo             self.create_manifest^(^)
echo             print^("\\n🎉 נתוני האתר מוכנים!"^)
echo             return True
echo         except Exception as e:
echo             print^(f"\\n❌ שגיאה: {e}"^)
echo             return False
echo         finally:
echo             if self.conn: self.conn.close^(^)
echo.
echo def main^(^):
echo     builder = TorahWebsiteBuilder^(^)
echo     success = builder.build_website_data^(^)
echo     if success:
echo         print^("\\n🎯 הנתונים מוכנים לאתר!"^)
echo         print^("\\n🚀 השלב הבא: בדיקת האתר!"^)
echo     return success
echo.
echo if __name__ == "__main__":
echo     main^(^)
) > torah_website_builder.py

echo ✅ נוצר קובץ torah_website_builder.py
echo.

REM שלב 3: הרצת הסקריפט
echo 🚀 שלב 3: מריץ סקריפט בניית הנתונים...
echo.
python torah_website_builder.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ שגיאה בהרצת הסקריפט!
    echo בדוק שיש לך Python מותקן ושהקובץ torah.db תקין.
    pause
    exit /b 1
)

echo.
echo 🎉 הסקריפט הסתיים בהצלחה!
echo.

REM שלב 4: בדיקה שהנתונים נוצרו
echo 🔍 שלב 4: בודק שהנתונים נוצרו...

if exist "website_data\api\books_index.json" (
    echo ✅ נתוני האתר נוצרו בהצלחה!
) else (
    echo ❌ הנתונים לא נוצרו כהלכה
    pause
    exit /b 1
)

echo.
echo 🌐 שלב 5: מפעיל את השרת המקומי...
echo.
echo 🚀 האתר יפתח בדפדפן בכתובת: http://localhost:8000
echo.
echo ⚠️  כדי לעצור את השרת: לחץ Ctrl+C
echo.

REM פתיחת הדפדפן אחרי 3 שניות
timeout /t 3 /nobreak > nul
start http://localhost:8000

REM הפעלת השרת
echo 🌐 מפעיל שרת...
python -m http.server 8000

echo.
echo 👋 השרת נסגר. להפעלה מחדש הרץ שוב את הסקריפט!
pause
