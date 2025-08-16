#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ייצוא מלא ומושלם של כל נתוני התורה ל-JSON
יוצר גיבוי מלא של כל המידע במבנה מאורגן ונוח
"""

import sqlite3
import json
import os
from datetime import datetime
from collections import defaultdict

class CompleteTorahJSONExporter:
    def __init__(self, db_path="torah.db", output_dir="torah_json_export"):
        self.db_path = db_path
        self.output_dir = output_dir
        self.conn = None
        self.export_stats = {
            "exported_at": datetime.now().isoformat(),
            "total_files": 0,
            "total_size_mb": 0,
            "tables_exported": {},
            "records_count": {}
        }
        
    def connect_db(self):
        """התחברות לבסיס הנתונים"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"קובץ {self.db_path} לא נמצא!")
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ מחובר ל-{self.db_path}")
        
    def setup_output_directory(self):
        """יצירת תיקיות פלט"""
        directories = [
            self.output_dir,
            f"{self.output_dir}/tables",          # טבלאות נפרדות
            f"{self.output_dir}/structured",      # נתונים מבניים
            f"{self.output_dir}/complete",        # קובץ אחד עם הכל
            f"{self.output_dir}/books_separate",  # כל ספר בנפרד
            f"{self.output_dir}/backup"           # גיבוי גולמי
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"📁 נוצרה תיקייה: {directory}")
    
    def save_json(self, data, filepath, compress=False):
        """שמירת JSON עם אופציה לדחיסה"""
        full_path = f"{self.output_dir}/{filepath}"
        
        if compress:
            import gzip
            with gzip.open(f"{full_path}.gz", 'wt', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            file_size = os.path.getsize(f"{full_path}.gz")
            self.export_stats["total_files"] += 1
            self.export_stats["total_size_mb"] += file_size / (1024*1024)
            return f"{filepath}.gz"
        else:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            file_size = os.path.getsize(full_path)
            self.export_stats["total_files"] += 1
            self.export_stats["total_size_mb"] += file_size / (1024*1024)
            return filepath
    
    def export_all_tables_raw(self):
        """ייצוא כל הטבלאות בצורה גולמית"""
        print("\n📊 מייצא את כל הטבלאות...")
        
        cursor = self.conn.cursor()
        
        # קבלת רשימת כל הטבלאות
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        all_tables_data = {}
        
        for table_name in tables:
            print(f"  📋 מייצא טבלה: {table_name}")
            
            # ייצוא מלא של הטבלה
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = [dict(row) for row in cursor.fetchall()]
            
            # מידע על הטבלה
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = [dict(row) for row in cursor.fetchall()]
            
            table_data = {
                "table_name": table_name,
                "columns": columns_info,
                "row_count": len(rows),
                "data": rows
            }
            
            all_tables_data[table_name] = table_data
            self.export_stats["records_count"][table_name] = len(rows)
            
            # שמירה נפרדת של כל טבלה
            self.save_json(table_data, f"tables/{table_name}.json")
            
            print(f"    ✅ {len(rows):,} רשומות נשמרו")
        
        # שמירה של כל הטבלאות ביחד (דחוס)
        self.save_json(all_tables_data, "backup/all_tables_raw", compress=True)
        print(f"  💾 כל הטבלאות נשמרו גם ביחד (דחוס)")
        
        return all_tables_data
    
    def create_structured_export(self):
        """יצירת ייצוא מובנה עם קשרים"""
        print("\n🏗️ יוצר ייצוא מובנה...")
        
        cursor = self.conn.cursor()
        
        structured_data = {
            "metadata": {
                "export_date": self.export_stats["exported_at"],
                "source_database": self.db_path,
                "description": "נתוני התורה המלאים במבנה מובנה"
            },
            "books": [],
            "parshiot": [],
            "statistics": {}
        }
        
        # ייצוא ספרים עם כל הנתונים
        cursor.execute("SELECT * FROM tbl_Sefer ORDER BY ID")
        books = cursor.fetchall()
        
        total_verses = 0
        total_questions = 0
        total_titles = 0
        
        for book in books:
            book_id = book["ID"]
            book_name = book["SeferName"]
            
            print(f"  📚 מעבד ספר: {book_name}")
            
            book_data = {
                "book_info": dict(book),
                "chapters": [],
                "statistics": {
                    "chapter_count": 0,
                    "verse_count": 0,
                    "question_count": 0,
                    "title_count": 0
                }
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
                    titles = [dict(row) for row in cursor.fetchall()]
                    
                    # קבלת שאלות לכל כותרת
                    verse_questions = []
                    for title in titles:
                        cursor.execute("SELECT * FROM tbl_Question WHERE TitleID = ?", (title["ID"],))
                        questions = [dict(row) for row in cursor.fetchall()]
                        
                        if questions:  # רק אם יש שאלות
                            verse_questions.append({
                                "title_info": title,
                                "questions": questions
                            })
                    
                    verse_data = {
                        "torah_id": torah_id,
                        "verse_number": verse_num,
                        "text": verse_text,
                        "titles": titles,
                        "question_groups": verse_questions,
                        "stats": {
                            "title_count": len(titles),
                            "question_count": sum(len(qg["questions"]) for qg in verse_questions)
                        }
                    }
                    
                    chapter_data["verses"].append(verse_data)
                    
                    # עדכון סטטיסטיקות
                    book_data["statistics"]["title_count"] += len(titles)
                    book_data["statistics"]["question_count"] += verse_data["stats"]["question_count"]
                
                book_data["chapters"].append(chapter_data)
                book_data["statistics"]["verse_count"] += len(verses)
            
            book_data["statistics"]["chapter_count"] = len(chapters)
            structured_data["books"].append(book_data)
            
            # עדכון סטטיסטיקות כלליות
            total_verses += book_data["statistics"]["verse_count"]
            total_questions += book_data["statistics"]["question_count"]
            total_titles += book_data["statistics"]["title_count"]
            
            print(f"    ✅ {book_name}: {book_data['statistics']['chapter_count']} פרקים, {book_data['statistics']['verse_count']} פסוקים, {book_data['statistics']['question_count']} שאלות")
        
        # ייצוא פרשות
        cursor.execute("""
            SELECT p.*, s.SeferName 
            FROM tbl_Parsha p
            JOIN tbl_Sefer s ON p.SeferID = s.ID
            ORDER BY p.ID
        """)
        parshiot = [dict(row) for row in cursor.fetchall()]
        structured_data["parshiot"] = parshiot
        
        # סטטיסטיקות כלליות
        structured_data["statistics"] = {
            "total_books": len(books),
            "total_chapters": sum(book["statistics"]["chapter_count"] for book in structured_data["books"]),
            "total_verses": total_verses,
            "total_questions": total_questions,
            "total_titles": total_titles,
            "total_parshiot": len(parshiot)
        }
        
        # שמירה של הייצוא המובנה (דחוס - כי זה גדול)
        self.save_json(structured_data, "structured/complete_torah_structured", compress=True)
        
        print(f"  💾 ייצוא מובנה נשמר (דחוס)")
        print(f"  📊 סטטיסטיקות: {structured_data['statistics']}")
        
        return structured_data
    
    def create_separate_books(self, structured_data):
        """יצירת קובץ נפרד לכל ספר"""
        print("\n📖 יוצר קבצים נפרדים לכל ספר...")
        
        for book in structured_data["books"]:
            book_name = book["book_info"]["SeferName"]
            book_id = book["book_info"]["ID"]
            
            book_file_data = {
                "book_info": book["book_info"],
                "chapters": book["chapters"],
                "statistics": book["statistics"],
                "export_info": {
                    "exported_at": self.export_stats["exported_at"],
                    "book_name": book_name,
                    "book_id": book_id
                }
            }
            
            filename = f"books_separate/book_{book_id}_{book_name}.json"
            self.save_json(book_file_data, filename, compress=True)
            
            print(f"  📚 {book_name} נשמר בנפרד")
    
    def create_complete_single_file(self, all_tables, structured_data):
        """יצירת קובץ אחד עם כל המידע"""
        print("\n📦 יוצר קובץ אחד עם כל המידע...")
        
        complete_data = {
            "export_info": {
                "exported_at": self.export_stats["exported_at"],
                "exporter_version": "1.0",
                "source_database": self.db_path,
                "description": "ייצוא מלא ומושלם של כל נתוני התורה"
            },
            "raw_tables": all_tables,
            "structured_data": structured_data,
            "export_statistics": self.export_stats
        }
        
        # שמירה עם דחיסה מקסימלית
        self.save_json(complete_data, "complete/torah_complete_export", compress=True)
        
        print(f"  💾 קובץ מלא נוצר (דחוס)")
    
    def create_export_manifest(self):
        """יצירת קובץ מניפסט עם תיאור כל הקבצים"""
        print("\n📋 יוצר מניפסט ייצוא...")
        
        manifest = {
            "export_info": {
                "created": self.export_stats["exported_at"],
                "total_files": self.export_stats["total_files"],
                "total_size_mb": round(self.export_stats["total_size_mb"], 2),
                "database_source": self.db_path
            },
            "files_structure": {
                "tables/": "כל טבלה בקובץ נפרד (JSON רגיל)",
                "structured/": "נתונים מובנים עם קשרים (JSON דחוס)",
                "books_separate/": "כל ספר בקובץ נפרד (JSON דחוס)",
                "complete/": "קובץ אחד עם כל המידע (JSON דחוס)",
                "backup/": "גיבוי גולמי של כל הטבלאות (JSON דחוס)"
            },
            "recommended_usage": {
                "for_development": "השתמש בקבצים מ-structured/ או books_separate/",
                "for_backup": "השתמש בקובץ מ-complete/",
                "for_analysis": "השתמש בקבצים מ-tables/",
                "for_restore": "השתמש בקובץ מ-backup/"
            },
            "statistics": self.export_stats["records_count"],
            "next_steps": [
                "בדוק את structured/complete_torah_structured.json.gz לנתונים מובנים",
                "השתמש ב-books_separate/ לפיתוח אתר",
                "שמור את complete/ כגיבוי",
                "הקובץ הזה (manifest.json) מכיל הסבר על כל הקבצים"
            ]
        }
        
        self.save_json(manifest, "manifest.json")
        print(f"  ✅ מניפסט נוצר")
        
        return manifest
    
    def export_all(self):
        """הרצת כל תהליכי הייצוא"""
        print("🚀 מתחיל ייצוא מלא של נתוני התורה ל-JSON")
        print("=" * 60)
        
        try:
            # 1. הכנות
            self.connect_db()
            self.setup_output_directory()
            
            # 2. ייצוא גולמי של כל הטבלאות
            all_tables = self.export_all_tables_raw()
            
            # 3. ייצוא מובנה עם קשרים
            structured_data = self.create_structured_export()
            
            # 4. קבצים נפרדים לכל ספר
            self.create_separate_books(structured_data)
            
            # 5. קובץ אחד עם הכל
            self.create_complete_single_file(all_tables, structured_data)
            
            # 6. מניפסט הסבר
            manifest = self.create_export_manifest()
            
            print(f"\n🎉 ייצוא הושלם בהצלחה!")
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
    print("📚 ייצוא מלא של נתוני התורה ל-JSON")
    print("יוצר גיבוי מושלם של כל המידע במבנה מאורגן")
    print("=" * 60)
    
    exporter = CompleteTorahJSONExporter()
    success = exporter.export_all()
    
    if success:
        print(f"\n🎯 הייצוא הושלם בהצלחה!")
        print(f"\n📁 נוצרו הקבצים:")
        print(f"  📊 tables/ - כל טבלה בנפרד")
        print(f"  🏗️ structured/ - נתונים מובנים")
        print(f"  📚 books_separate/ - כל ספר בנפרד") 
        print(f"  📦 complete/ - קובץ אחד עם הכל")
        print(f"  💾 backup/ - גיבוי גולמי")
        print(f"  📋 manifest.json - הסבר על כל הקבצים")
        
        print(f"\n📊 סטטיסטיקות:")
        print(f"  📁 קבצים שנוצרו: {exporter.export_stats['total_files']}")
        print(f"  💾 גודל כולל: {exporter.export_stats['total_size_mb']:.1f} MB")
        
        print(f"\n🚀 השלב הבא:")
        print(f"  בדוק את תיקיית torah_json_export/")
        print(f"  התחל עם manifest.json להבנת המבנה")
        print(f"  השתמש ב-structured/ לפיתוח האתר המתקדם")
        
    else:
        print(f"\n❌ הייצוא נכשל")

if __name__ == "__main__":
    main()
