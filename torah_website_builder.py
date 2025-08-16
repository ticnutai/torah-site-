#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import json
import os
from datetime import datetime

class TorahWebsiteBuilder:
    def __init__(self, db_path="torah.db", output_dir="website_data"):
        self.db_path = db_path
        self.output_dir = output_dir
        self.conn = None
        
    def connect_db(self):
        if not os.path.exists(self.db_path):
            print(f"❌ שגיאה: הקובץ {self.db_path} לא נמצא!")
            return False
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ מחובר ל-{self.db_path}")
        return True
    
    def setup_directories(self):
        directories = [self.output_dir, f"{self.output_dir}/books", f"{self.output_dir}/api"]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"📁 {directory}")
    
    def save_json(self, data, filepath):
        full_path = f"{self.output_dir}/{filepath}"
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath
    
    def create_slug(self, text):
        hebrew_to_english = {
            "בראשית": "genesis", "שמות": "exodus", "ויקרא": "leviticus",
            "במדבר": "numbers", "דברים": "deuteronomy"
        }
        return hebrew_to_english.get(text, text.lower().replace(" ", "-"))
    
    def create_books_index(self):
        print("\n📚 יוצר אינדקס ספרים...")
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tbl_Sefer ORDER BY ID")
        books = [dict(row) for row in cursor.fetchall()]
        books_index = {"books": []}
        
        for book in books:
            book_id = book["ID"]
            book_name = book["SeferName"]
            
            cursor.execute("SELECT COUNT(DISTINCT Perek) FROM tbl_Torah WHERE Sefer = ?", (book_id,))
            chapter_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tbl_Torah WHERE Sefer = ?", (book_id,))
            verse_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(q.ID) FROM tbl_Question q
                JOIN tbl_Title t ON q.TitleID = t.ID
                JOIN tbl_Torah tor ON t.TorahID = tor.ID
                WHERE tor.Sefer = ?""", (book_id,))
            question_count = cursor.fetchone()[0]
            
            book_info = {
                "id": book_id, "name": book_name, "slug": self.create_slug(book_name),
                "chapter_count": chapter_count, "verse_count": verse_count,
                "question_count": question_count, "file_path": f"books/book_{book_id}.json"
            }
            books_index["books"].append(book_info)
            print(f"  📖 {book_name}: {chapter_count} פרקים, {verse_count} פסוקים, {question_count} שאלות")
        
        self.save_json(books_index, "api/books_index.json")
        print("  ✅ אינדקס ספרים נשמר")
        return books_index
    
    def create_book_files(self, books_index):
        print("\n📖 יוצר קבצי ספרים...")
        cursor = self.conn.cursor()
        
        for book_info in books_index["books"][:2]:
            book_id = book_info["id"]
            book_name = book_info["name"]
            print(f"  📚 מעבד ספר: {book_name}")
            
            book_data = {"book_info": book_info, "chapters": []}
            
            cursor.execute("SELECT DISTINCT Perek FROM tbl_Torah WHERE Sefer = ? ORDER BY Perek LIMIT 2", (book_id,))
            chapters = [row[0] for row in cursor.fetchall()]
            
            for chapter_num in chapters:
                chapter_data = {"chapter_number": chapter_num, "verses": []}
                
                cursor.execute("SELECT ID, PasukNum, Pasuk FROM tbl_Torah WHERE Sefer = ? AND Perek = ? ORDER BY PasukNum LIMIT 5", (book_id, chapter_num))
                verses = cursor.fetchall()
                
                for verse in verses:
                    torah_id, verse_num, verse_text = verse["ID"], verse["PasukNum"], verse["Pasuk"]
                    
                    cursor.execute("SELECT COUNT(*) FROM tbl_Title WHERE TorahID = ?", (torah_id,))
                    question_count = cursor.fetchone()[0]
                    
                    verse_data = {
                        "verse_number": verse_num, "text": verse_text, "torah_id": torah_id,
                        "total_questions": question_count, "question_groups": []
                    }
                    
                    if question_count > 0:
                        verse_data["question_groups"] = [{"title": "שאלות", "questions": [f"שאלה מספר {i+1}" for i in range(min(3, question_count))]}]
                    
                    chapter_data["verses"].append(verse_data)
                
                book_data["chapters"].append(chapter_data)
            
            self.save_json(book_data, f"books/book_{book_id}.json")
            print(f"    ✅ {len(book_data['chapters'])} פרקים נשמרו")
    
    def create_parshiot_data(self):
        print("\n📜 יוצר נתוני פרשות...")
        cursor = self.conn.cursor()
        cursor.execute("SELECT p.*, s.SeferName FROM tbl_Parsha p JOIN tbl_Sefer s ON p.SeferID = s.ID ORDER BY p.ID")
        parshiot = []
        
        for row in cursor.fetchall():
            parsha_data = {
                "id": row["ID"], "name": row["ParshaName"], "sefer_id": row["SeferID"],
                "sefer_name": row["SeferName"], "start_chapter": row["StartPerek"], "start_verse": row["StartPasuk"]
            }
            parshiot.append(parsha_data)
        
        parshiot_data = {"parshiot": parshiot, "total_count": len(parshiot)}
        self.save_json(parshiot_data, "api/parshiot.json")
        print(f"  ✅ {len(parshiot)} פרשות נשמרו")
    
    def create_manifest(self):
        manifest = {
            "version": "1.0", "created": datetime.now().isoformat(),
            "description": "נתוני תורה מוכנים לאתר"
        }
        self.save_json(manifest, "manifest.json")
        print("  ✅ מניפסט נוצר")
    
    def build_website_data(self):
        print("🌐 בונה נתונים לאתר התורה")
        print("=" * 50)
        try:
            if not self.connect_db(): return False
            self.setup_directories()
            books_index = self.create_books_index()
            self.create_book_files(books_index)
            self.create_parshiot_data()
            self.create_manifest()
            print("\n🎉 נתוני האתר מוכנים!")
            return True
        except Exception as e:
            print(f"\n❌ שגיאה: {e}")
            return False
        finally:
            if self.conn: self.conn.close()

def main():
    builder = TorahWebsiteBuilder()
    success = builder.build_website_data()
    if success:
        print("\n🎯 הנתונים מוכנים לאתר!")
        print("\n🚀 הרץ: python -m http.server 8000")

if __name__ == "__main__":
    main()
