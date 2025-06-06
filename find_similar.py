import sqlite3
import pandas as pd
import re
from sentence_transformers import SentenceTransformer, util
import numpy as np


# Завантаження моделі — глобально (може тривати кілька секунд, але лише раз)
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def find_ukr_matches_for_jp_input(query_text, category=None, top_k=5):
    # Підключення до бази даних
    conn = sqlite3.connect("combined_dictionary.db")
    cursor = conn.cursor()
    query_text = query_text.strip().lower() if query_text else ""
    
    # Випадок: якщо слово не задане, але задана категорія
    if not query_text and category:
        rows = pd.read_sql_query("""
            SELECT hiragana, katakana, romaji, definition, category, examples, examples_translation, similar, source
            FROM merged_onomatopoeia
            WHERE category = ?
        """, conn, params=(category,))
        
        results = []
        for i, row in rows.iterrows():
            hira_list = [x.strip() for x in re.split(r'[/\s]', row['hiragana'] or '') if x.strip()]
            result = {
                "match": {
                    "hiragana": hira_list[0] if hira_list else '',
                    "katakana": row['katakana'],
                    "romaji": row['romaji']
                },
                "synonyms": hira_list[1:] if len(hira_list) > 1 else [],
                "definition": row['definition'],
                "category": row['category'],
                "examples": row['examples'],
                "examples_translation": row['examples_translation'],
                "source": row['source'],
                "ukrainian_matches": []
            }
            results.append(result)
        
        conn.close()
        return {"query": query_text, "category": category, "results": results}

    # Інакше — повний семантичний пошук

    query_emb = model.encode(query_text)

    # 1. Завантажити японські слова
    jp_rows = pd.read_sql_query("""
        SELECT hiragana, katakana, romaji, definition, category, examples, examples_translation, similar, source
        FROM merged_onomatopoeia
    """, conn)

    # 2. Завантажити кешовані ембединги з бази
    cursor.execute("SELECT query_form, embedding FROM jp_embeddings")
    embedding_cache = {
        row[0]: np.frombuffer(row[1], dtype='float32')
        for row in cursor.fetchall()
    }
    candidates = []
    
    for _, row in jp_rows.iterrows():
        if category and row['category'] != category:
            continue
        for col in ['hiragana', 'katakana', 'romaji']:
            val = row[col]
            if not val:
                continue
            for part in re.split(r'[/\s]', val.lower()):
                if not part or part not in embedding_cache:
                    continue
                sim = util.cos_sim(embedding_cache[part], query_emb).item()
                if query_text in part:
                    candidates.append({
                        "matched_part": part,
                        "full_row": row,
                        "score": sim,
                        "length": len(part)
                    })

    if not candidates:
        conn.close()
        return {"query": query_text, "category": category, "results": [], "message": "Не знайдено відповідників"}

    sorted_matches = sorted(candidates, key=lambda x: (-x["score"], x["length"]))

    results = []
    for i, match in enumerate(sorted_matches):
        row = match["full_row"]
        matched_part = match["matched_part"]

        hira_list = re.split(r'[/\s]', row['hiragana']) if row['hiragana'] else []
        kata_list = re.split(r'[/\s]', row['katakana']) if row['katakana'] else []
        roma_list = re.split(r'[/\s]', row['romaji']) if row['romaji'] else []

        hira_list = [x.strip() for x in hira_list if x.strip()]
        kata_list = [x.strip() for x in kata_list if x.strip()]
        roma_list = [x.strip() for x in roma_list if x.strip()]

        if matched_part in hira_list:
            idx = hira_list.index(matched_part)
        elif matched_part in kata_list:
            idx = kata_list.index(matched_part)
        elif matched_part in roma_list:
            idx = roma_list.index(matched_part)
        else:
            idx = None

        hira = hira_list[idx] if idx is not None and idx < len(hira_list) else ''
        kata = kata_list[idx] if idx is not None and idx < len(kata_list) else ''
        roma = roma_list[idx] if idx is not None and idx < len(roma_list) else ''
        synonyms = [h for j, h in enumerate(hira_list) if j != idx]

        # Пошук відповідників
        ukr_matches = pd.read_sql_query("""
            SELECT ukr_word, ukr_definition, similarity
            FROM semantic_similarity
            WHERE category = ? AND jap_definition = ?
            ORDER BY similarity DESC
            LIMIT ?
        """, conn, params=(row['category'], row['definition'], top_k))

        ukr_list = [
            {
                "word": u.ukr_word,
                "definition": u.ukr_definition,
                "similarity": round(u.similarity, 3)
            }
            for u in ukr_matches.itertuples()
        ]

        result = {
            "match": {
                "hiragana": hira,
                "katakana": kata,
                "romaji": roma
            },
            "synonyms": synonyms,
            "definition": row['definition'],
            "category": row['category'],
            "examples": row['examples'],
            "examples_translation": row['examples_translation'],
            "source": row['source'],
            "ukrainian_matches": ukr_list
        }

        results.append(result)

    return {"query": query_text, "category": category, "results": results}

print(find_ukr_matches_for_jp_input('nyaa', 'Звірі'))