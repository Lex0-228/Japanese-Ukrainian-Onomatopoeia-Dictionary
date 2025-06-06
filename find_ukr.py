import sqlite3
import pandas as pd
import re



def find_ukrainian_words(query_text=None, category=None):
    # Підключення до бази даних
    conn = sqlite3.connect("combined_dictionary.db")
    cursor = conn.cursor()
    query_text = query_text.strip().lower() if query_text else None
    category = category.strip().lower() if category else None

    # Завантаження українських слів
    df = pd.read_sql_query("""
        SELECT word, definition, category, examples, source
        FROM merged_ukrainian_onomatopoeia
    """, conn)

    def word_matches(row):
        if not query_text:
            return True
        parts = re.split(r'[/\s]', row['word'].lower())
        return any(query_text in part for part in parts)

    def category_matches(row):
        return category in row['category'].lower() if category and row['category'] else not category

    filtered = df[df.apply(lambda row: word_matches(row) and category_matches(row), axis=1)]
    
    if filtered.empty:
        return {"query": query_text, "category": category, "results": [], "message": "Не знайдено відповідників"}

    # Сортування за словом
    filtered_sorted = filtered.sort_values(by="word")

    results = []
    for i, row in enumerate(filtered_sorted.itertuples(), 1):
        results.append({
            "index": i,
            "word": row.word,
            "definition": row.definition,
            "category": row.category,
            "examples": row.examples if row.examples else None,
            "source": row.source
        })
    conn.close()
    return {"query": query_text, "category": category, "results": results}

