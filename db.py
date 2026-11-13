import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

DB_PATH = Path(os.environ.get("DB_PATH", Path(__file__).parent / "recipes.db"))

def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                video_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                channel_name TEXT,
                channel_id TEXT,
                published_at TEXT,
                thumbnail_url TEXT,
                description TEXT,
                raw_ingredients_text TEXT
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                ingredient_name TEXT NOT NULL,
                raw_line TEXT,
                FOREIGN KEY (video_id) REFERENCES recipes(video_id) ON DELETE CASCADE
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recipe_ing_video ON recipe_ingredients(video_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recipe_ing_name ON recipe_ingredients(ingredient_name);")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS custom_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL,
                ingredient_name TEXT NOT NULL UNIQUE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_pantry (
                ingredient_name TEXT PRIMARY KEY
            );
        """)
    conn.close()

def save_recipe(
    video_id: str,
    title: str,
    channel_name: str,
    channel_id: str,
    published_at: str,
    thumbnail_url: str,
    description: str,
    raw_ingredients_text: str,
    ingredients: List[Dict[str, str]]
):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO recipes (video_id, title, channel_name, channel_id, published_at, thumbnail_url, description, raw_ingredients_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                title=excluded.title,
                channel_name=excluded.channel_name,
                thumbnail_url=excluded.thumbnail_url,
                description=excluded.description,
                raw_ingredients_text=excluded.raw_ingredients_text
        """, (video_id, title, channel_name, channel_id, published_at, thumbnail_url, description, raw_ingredients_text))
        
        # Clear previous ingredients and re-insert
        conn.execute("DELETE FROM recipe_ingredients WHERE video_id = ?", (video_id,))
        for ing in ingredients:
            conn.execute("""
                INSERT INTO recipe_ingredients (video_id, ingredient_name, raw_line)
                VALUES (?, ?, ?)
            """, (video_id, ing["name"], ing.get("raw_line", "")))
    conn.close()

def get_all_recipes_with_ingredients() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes ORDER BY published_at DESC")
    recipes_rows = cursor.fetchall()
    
    results = []
    for r in recipes_rows:
        rec = dict(r)
        cursor.execute("SELECT ingredient_name, raw_line FROM recipe_ingredients WHERE video_id = ?", (rec["video_id"],))
        ings = cursor.fetchall()
        rec["ingredients"] = [row["ingredient_name"] for row in ings]
        rec["ingredient_details"] = [{"name": row["ingredient_name"], "raw": row["raw_line"]} for row in ings]
        results.append(rec)
    conn.close()
    return results

def get_unique_ingredients() -> List[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ingredient_name FROM recipe_ingredients ORDER BY ingredient_name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [r["ingredient_name"] for r in rows]

def get_saved_video_ids() -> Set[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT video_id FROM recipes")
    rows = cursor.fetchall()
    conn.close()
    return {r["video_id"] for r in rows}

def get_stats() -> Dict[str, int]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM recipes")
    recipes_count = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(DISTINCT ingredient_name) as count FROM recipe_ingredients")
    ingredients_count = cursor.fetchone()["count"]
    conn.close()
    return {"recipes": recipes_count, "ingredients": ingredients_count}

def add_custom_ingredient(category_name: str, ingredient_name: str) -> bool:
    name = ingredient_name.lower().strip()
    if not name:
        return False
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO custom_ingredients (category_name, ingredient_name)
            VALUES (?, ?)
            ON CONFLICT(ingredient_name) DO UPDATE SET category_name=excluded.category_name
        """, (category_name.strip(), name))
    conn.close()
    return True

def get_custom_ingredients() -> Dict[str, List[str]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category_name, ingredient_name FROM custom_ingredients ORDER BY ingredient_name ASC")
    rows = cursor.fetchall()
    conn.close()
    result = {}
    for r in rows:
        cat = r["category_name"]
        if cat not in result:
            result[cat] = []
        result[cat].append(r["ingredient_name"])
    return result

def delete_custom_ingredient(ingredient_name: str):
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM custom_ingredients WHERE ingredient_name = ?", (ingredient_name.lower().strip(),))
    conn.close()

def get_user_pantry() -> Set[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ingredient_name FROM user_pantry")
    rows = cursor.fetchall()
    conn.close()
    return {r["ingredient_name"] for r in rows}

def toggle_user_pantry_item(ingredient_name: str, is_active: bool):
    name = ingredient_name.lower().strip()
    if not name:
        return
    conn = get_connection()
    with conn:
        if is_active:
            conn.execute("INSERT OR IGNORE INTO user_pantry (ingredient_name) VALUES (?)", (name,))
        else:
            conn.execute("DELETE FROM user_pantry WHERE ingredient_name = ?", (name,))
    conn.close()

def clear_user_pantry():
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM user_pantry")
    conn.close()
