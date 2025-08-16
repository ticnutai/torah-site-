#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ייצוא מלא של כל נתוני התורה ל-JSON
יוצר backup מקיף של כל המידע מבסיס הנתונים
"""

import sqlite3
import json
import os
from datetime import datetime
from collections import defaultdict

class FullTorahJSONExporter:
    def __init__(self, db_path="torah.db", output_dir="torah_full_export"):
        self.db_path = db_path
        self.output_dir = output_dir
        self.conn = None
        self.stats = {}
        
    def connect_db(self):
        """התחברות לבסיס הנתונים"""
        if not os.path.exists(self.db_path):
            print(f"❌ שגיאה: הקובץ {self.db_path} לא נמצא!")
            return False
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ מחובר ל-{self.db_path}")
        return True
    
    def setup_directories(self):
        """יצירת תיקיות הפלט"""
        directories = [
            self.output_dir,
            f"{self.output_dir}/complete",     # הכל במקום אחד
            f"{self.output_dir}/separated",    # כל טבלה בנפרד
            f"{self.output_dir}/structured"    # מבנה היררכי
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"📁 {directory}")
    
    def save_json(self, data, filepath, pretty=True):
        """שמירת JSON עם אופציה לפורמט יפה או קומפקטי"""
        full_path = f"{self.output_dir}/{filepath}"
        
        if pretty:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        
        # חישוב גודל
        size = os.path.getsize(full_path)
        print(f"  💾 {filepath}: {size:,} בתים ({size/1024:.1f} KB)")
        return size
    
    def export_raw_tables(self):
        """ייצוא גולמי של כל הטבלאות"""
        print("\n📊 מייצא טבלאות גולמיות...")
        
        cursor = self.conn.cursor()
        
        # קבלת רשימת טבלאות
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        raw_export = {
            "export_info": {
                "created": datetime.now().isoformat(),
                "source_db": self.db_path,
                "total_tables": len(tables)
            },
            "tables": {}
        }
        
        total_records = 0
        
        for table_name in tables:
            print(f"  📋 מייצא טבלה: {table_name}")
            
            # קבלת כל הנתונים
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = [dict(row) for row in cursor.fetchall()]
            
            # מידע על הטבלה
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = [dict(row) for row in cursor.fetchall()]
            
            raw_export["tables"][table_name] = {
                "columns": columns_info,
                "record_count": len(rows),
                "data": rows
            }
            
            total_records += len(rows)
            print(f"    ✅ {len(rows):,} רשומות")
            
            # שמירה נפרדת של כל טבלה
            table_data = {
                "table_name": table_name,
                "columns": columns_info,
                "record_count": len(rows),
                "exported": datetime.now().isoformat(),
                "data": rows
            }
            self.save_json(table_data, f"separated/{table_name}.json")
        
        raw_export["export_info"]["total_records"] = total_records
        self.stats["raw_export"] = {"tables": len(tables), "records": total_records}
        
        # שמירת הייצוא המלא
        size = self.save_json(raw_export, "complete/all_tables_raw.json")
        self.stats["raw_export"]["size"] = size
        
        print(f"  🎉 סיכום: {len(tables)} טבלאות, {total_records:,} רשומות")
        return raw_export
    
    def export_structured_torah(self):
        """ייצוא מובנה של התורה - ספרים->פרקים->פסוקים->שאלות"""
        print("\n📚 מייצא מבנה תורה מובנה...")
        
        cursor = self.conn.cursor()
        
        structured_torah = {
            "export_info": {
                "created": datetime.now().isoformat(),
                "type": "structured_torah",
                "description": "התורה במבנה היררכי מלא"
            },
            "books": []
        }
        
        # קבלת כל הספרים
        cursor.execute("SELECT * FROM tbl_Sefer ORDER BY ID")
        books = cursor.fetchall()
        
        total_chapters = 0
        total_verses = 0
        total_questions = 0
        
        for book in books:
            book_id = book["ID"]
            book_name = book["SeferName"]
            
            print(f"  📖 מעבד ספר: {book_name}")
            
            book_data = {
                "book_info": dict(book),
                "chapters": []
            }
            
            # קבלת כל הפרקים
            cursor.execute("SELECT DISTINCT Perek FROM tbl_Torah WHERE Sefer = ? ORDER BY Perek", (book_id,))
            chapters = [row[0] for row in cursor.fetchall()]
            
            for chapter_num in chapters:
                chapter_data = {
                    "chapter_number": chapter_num,
                    "verses": []
                }
                
                # קבלת כל הפסוקים בפרק
                cursor.execute("""
                    SELECT ID, PasukNum, Pasuk 
                    FROM tbl_Torah 
                    WHERE Sefer = ? AND Perek = ? 
                    ORDER BY PasukNum
                """, (book_id, chapter_num))
                
                verses = cursor.fetchall()
                
                for verse in verses:
                    torah_id = verse["ID"]
                    verse_num = verse["PasukNum"]
                    verse_text = verse["Pasuk"]
                    
                    # קבלת כותרות לפסוק
                    cursor.execute("SELECT * FROM tbl_Title WHERE TorahID = ?", (torah_id,))
                    titles = cursor.fetchall()
                    
                    # קבלת שאלות לכל כותרת
                    verse_content = {
                        "verse_number": verse_num,
                        "text": verse_text,
                        "torah_id": torah_id,
                        "titles_and_questions": []
                    }
                    
                    verse_question_count = 0
                    
                    for title in titles:
                        title_id = title["ID"]
                        title_text = title["Title"]
                        
                        # קבלת שאלות לכותרת
                        cursor.execute("SELECT * FROM tbl_Question WHERE TitleID = ?", (title_id,))
                        questions = cursor.fetchall()
                        
                        if questions:  # רק אם יש שאלות
                            title_content = {
                                "title_info": dict(title),
                                "questions": [dict(q) for q in questions]
                            }
                            verse_content["titles_and_questions"].append(title_content)
                            verse_question_count += len(questions)
                    
                    verse_content["total_questions"] = verse_question_count
                    chapter_data["verses"].append(verse_content)
                    
                    total_verses += 1
                    total_questions += verse_question_count
                
                book_data["chapters"].append(chapter_data)
                total_chapters += 1
                
                print(f"    ✅ פרק {chapter_num}: {len(verses)} פסוקים")
            
            structured_torah["books"].append(book_data)
            print(f"    🎉 {book_name}: {len(chapters)} פרקים הושלמו")
        
        # הוספת סטטיסטיקות
        structured_torah["statistics"] = {
            "total_books": len(books),
            "total_chapters": total_chapters,
            "total_verses": total_verses,
            "total_questions": total_questions
        }
        
        self.stats["structured"] = {
            "books": len(books),
            "chapters": total_chapters,
            "verses": total_verses,
            "questions": total_questions
        }
        
        # שמירה
        size = self.save_json(structured_torah, "structured/complete_torah_structured.json")
        self.stats["structured"]["size"] = size
        
        print(f"  🎊 סיכום מבנה: {len(books)} ספרים, {total_chapters} פרקים, {total_verses:,} פסוקים, {total_questions:,} שאלות")
        return structured_torah
    
    def export_parshiot_complete(self):
        """ייצוא מלא של פרשות השבוע"""
        print("\n📜 מייצא פרשות השבוע...")
        
        cursor = self.conn.cursor()
        
        # מטבלה tbl_Parsha
        cursor.execute("""
            SELECT p.*, s.SeferName 
            FROM tbl_Parsha p
            JOIN tbl_Sefer s ON p.SeferID = s.ID
            ORDER BY p.ID
        """)
        parshiot_main = [dict(row) for row in cursor.fetchall()]
        
        # מטבלה Parshiot (אם שונה)
        try:
            cursor.execute("""
                SELECT par.*, s.SeferName 
                FROM Parshiot par
                JOIN tbl_Sefer s ON par.SeferID = s.ID
                ORDER BY par.ID
            """)
            parshiot_alt = [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            parshiot_alt = []
        
        parshiot_export = {
            "export_info": {
                "created": datetime.now().isoformat(),
                "type": "parshiot_complete"
            },
            "parshiot_main_table": parshiot_main,
            "parshiot_alternative_table": parshiot_alt,
            "statistics": {
                "main_count": len(parshiot_main),
                "alternative_count": len(parshiot_alt)
            }
        }
        
        size = self.save_json(parshiot_export, "complete/parshiot_complete.json")
        self.stats["parshiot"] = {"count": len(parshiot_main), "size": size}
        
        print(f"  ✅ {len(parshiot_main)} פרשות עיקריות, {len(parshiot_alt)} נוספות")
        return parshiot_export
    
    def export_search_optimized(self):
        """ייצוא מותאם לחיפוש"""
        print("\n🔍 מייצא נתונים מותאמים לחיפוש...")
        
        cursor = self.conn.cursor()
        
        # אינדקס פסוקים לחיפוש
        cursor.execute("""
            SELECT 
                tor.ID as torah_id,
                tor.Sefer as book_id,
                s.SeferName as book_name,
                tor.Perek as chapter,
                tor.PasukNum as verse,
                tor.Pasuk as text
            FROM tbl_Torah tor
            JOIN tbl_Sefer s ON tor.Sefer = s.ID
            ORDER BY tor.Sefer, tor.Perek, tor.PasukNum
        """)
        
        verses_search = [dict(row) for row in cursor.fetchall()]
        
        # אינדקס שאלות לחיפוש
        cursor.execute("""
            SELECT 
                q.ID as question_id,
                q.Question as question_text,
                t.Title as title,
                t.TorahID as torah_id,
                tor.Sefer as book_id,
                s.SeferName as book_name,
                tor.Perek as chapter,
                tor.PasukNum as verse
            FROM tbl_Question q
            JOIN tbl_Title t ON q.TitleID = t.ID
            JOIN tbl_Torah tor ON t.TorahID = tor.ID
            JOIN tbl_Sefer s ON tor.Sefer = s.ID
            ORDER BY s.ID, tor.Perek, tor.PasukNum
        """)
        
        questions_search = [dict(row) for row in cursor.fetchall()]
        
        search_export = {
            "export_info": {
                "created": datetime.now().isoformat(),
                "type": "search_optimized",
                "description": "נתונים מותאמים לחיפוש מהיר"
            },
            "verses_index": verses_search,
            "questions_index": questions_search,
            "statistics": {
                "total_verses": len(verses_search),
                "total_questions": len(questions_search)
            }
        }
        
        size = self.save_json(search_export, "complete/search_optimized.json")
        self.stats["search"] = {"verses": len(verses_search), "questions": len(questions_search), "size": size}
        
        print(f"  ✅ {len(verses_search):,} פסוקים, {len(questions_search):,} שאלות לחיפוש")
        return search_export
    
    def create_export_summary(self):
        """יצירת סיכום הייצוא"""
        print("\n📋 יוצר סיכום הייצוא...")
        
        summary = {
            "export_summary": {
                "created": datetime.now().isoformat(),
                "source_database": self.db_path,
                "export_directory": self.output_dir,
                "export_types": [
                    "raw_tables", "structured_torah", "parshiot", "search_optimized"
                ]
            },
            "statistics": self.stats,
            "files_created": {
                "complete_exports": [
                    "complete/all_tables_raw.json",
                    "complete/parshiot_complete.json", 
                    "complete/search_optimized.json"
                ],
                "structured_export": [
                    "structured/complete_torah_structured.json"
                ],
                "separated_tables": [
                    "separated/tbl_Sefer.json",
                    "separated/tbl_Torah.json",
                    "separated/tbl_Question.json",
                    "separated/tbl_Title.json",
                    "separated/tbl_Parsha.json",
                    "separated/Parshiot.json"
                ]
            },
            "usage_recommendations": {
                "backup": "השתמש ב-complete/all_tables_raw.json לגיבוי מלא",
                "development": "השתמש ב-structured/complete_torah_structured.json לפיתוח אתר",
                "search": "השתמש ב-complete/search_optimized.json לחיפוש מהיר",
                "analysis": "השתמש בקבצים ב-separated/ לניתוח נתונים"
            }
        }
        
        size = self.save_json(summary, "export_summary.json")
        self.stats["summary_size"] = size
        
        return summary
    
    def export_all(self):
        """הרצת כל תהליכי הייצוא"""
        print("📦 מתחיל ייצוא מלא של כל נתוני התורה ל-JSON")
        print("=" * 60)
        
        try:
            # 1. התחברות
            if not self.connect_db():
                return False
            
            # 2. הכנת תיקיות
            self.setup_directories()
            
            # 3. ייצוא גולמי של טבלאות
            self.export_raw_tables()
            
            # 4. ייצוא מובנה של התורה
            self.export_structured_torah()
            
            # 5. ייצוא פרשות
            self.export_parshiot_complete()
            
            # 6. ייצוא לחיפוש
            self.export_search_optimized()
            
            # 7. סיכום
            self.create_export_summary()
            
            print("\n🎉 הייצוא הושלם בהצלחה!")
            return True
            
        except Exception as e:
            print(f"\n❌ שגיאה בייצוא: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.conn:
                self.conn.close()

def main():
    print("📦 ייצוא מלא של נתוני התורה ל-JSON")
    print("יוצר backup מקיף וקבצים לפיתוח")
    print("=" * 60)
    
    exporter = FullTorahJSONExporter()
    success = exporter.export_all()
    
    if success:
        print("\n🎯 הייצוא הושלם!")
        print(f"\n📁 קבצים נוצרו בתיקייה: {exporter.output_dir}/")
        
        print("\n📊 סיכום גדלי קבצים:")
        if exporter.stats:
            for category, data in exporter.stats.items():
                if isinstance(data, dict) and 'size' in data:
                    size_mb = data['size'] / (1024 * 1024)
                    print(f"  • {category}: {size_mb:.1f} MB")
        
        print("\n📋 קבצים עיקריים:")
        print(f"  🔹 torah_full_export/complete/all_tables_raw.json - גיבוי מלא")
        print(f"  🔹 torah_full_export/structured/complete_torah_structured.json - מבנה לאתר")
        print(f"  🔹 torah_full_export/complete/search_optimized.json - לחיפוש")
        print(f"  🔹 torah_full_export/export_summary.json - סיכום והנחיות")
        
        print(f"\n🚀 כעת תוכל להתחיל בשלב הבא - SQLite מוטמע!")
    else:
        print(f"\n❌ הייצוא נכשל. בדוק את השגיאות למעלה.")

if __name__ == "__main__":
    main()
