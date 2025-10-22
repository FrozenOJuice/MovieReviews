import os
import json
import uuid
import pandas as pd
from bs4 import BeautifulSoup

# ----------------------------------------
# Path setup (relative to backend/scripts/)
# ----------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
MOVIE_DATA_DIR = os.path.join(DATA_DIR, "movieData")

MOVIES_DIR = os.path.join(DATA_DIR, "movies")
REVIEWS_DIR = os.path.join(DATA_DIR, "reviews")
VOTES_DIR = os.path.join(DATA_DIR, "votes")

USERS_INACTIVE_PATH = os.path.join(DATA_DIR, "users_inactive.json")
USERS_ACTIVE_PATH = os.path.join(DATA_DIR, "users_active.json")

# ----------------------------------------
# Helper functions
# ----------------------------------------
def ensure_dirs():
    os.makedirs(MOVIES_DIR, exist_ok=True)
    os.makedirs(REVIEWS_DIR, exist_ok=True)
    os.makedirs(VOTES_DIR, exist_ok=True)

def clean_text(val: object) -> str:
    """Strip HTML and trim whitespace."""
    if not isinstance(val, str):
        return ""
    return BeautifulSoup(val, "html.parser").get_text().strip()

def load_users(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def save_users(path, users):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def find_user(users, username):
    """Return (index, user_dict) or (None, None)."""
    for i, u in enumerate(users):
        if u.get("username") == username:
            return i, u
    return None, None

def try_parse_int(val):
    try:
        if val is None:
            return None
        if isinstance(val, str):
            val = val.strip().replace(",", "")
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return None

def safe_int(val):
    if pd.isna(val):
        raise ValueError("NaN")
    if isinstance(val, str):
        val = val.strip()
    return int(val)

def to_iso_date(date_str: str) -> str:
    """Try to parse to YYYY-MM-DD, fallback to original cleaned."""
    s = clean_text(date_str)
    if not s:
        return ""
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.isna(dt):
            return s
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return s

# ----------------------------------------
# Migration Logic
# ----------------------------------------
def migrate_all_movies():
    ensure_dirs()

    inactive_users = load_users(USERS_INACTIVE_PATH)
    user_index = {u["username"]: u for u in inactive_users}

    for movie_folder in os.listdir(MOVIE_DATA_DIR):
        folder_path = os.path.join(MOVIE_DATA_DIR, movie_folder)
        metadata_path = os.path.join(folder_path, "metadata.json")
        reviews_path = os.path.join(folder_path, "movieReviews.csv")

        if not os.path.isdir(folder_path):
            continue
        if not os.path.exists(metadata_path) or not os.path.exists(reviews_path):
            print(f"⚠️ Skipping {movie_folder}: missing metadata or CSV.")
            continue

        # --- Movie metadata ---
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                md = json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading {movie_folder}/metadata.json: {e}")
            continue

        movie_id = str(uuid.uuid4())
        movie_doc = {
            "movie_id": movie_id,
            "title": md.get("title"),
            "imdb_rating": md.get("movieIMDbRating"),
            "meta_score": try_parse_int(md.get("metaScore")),
            "genres": md.get("movieGenres", []) or [],
            "directors": md.get("directors", []) or [],
            "release_date": md.get("datePublished"),
            "duration": md.get("duration"),
            "description": md.get("description"),
            "main_stars": md.get("mainStars", []) or [],
            "total_user_reviews": try_parse_int(md.get("totalUserReviews")),
            "total_critic_reviews": try_parse_int(md.get("totalCriticReviews")),
            "total_rating_count": try_parse_int(md.get("totalRatingCount")),
            "source_folder": movie_folder,
        }

        movie_out = os.path.join(MOVIES_DIR, f"{movie_id}.json")
        with open(movie_out, "w", encoding="utf-8") as f:
            json.dump(movie_doc, f, indent=4, ensure_ascii=False)

        # --- Reviews ---
        try:
            df = pd.read_csv(reviews_path, dtype=str, encoding_errors="ignore", on_bad_lines="skip")
        except TypeError:
            df = pd.read_csv(reviews_path, dtype=str, encoding_errors="ignore")

        col_map = {
            "Date of Review": ["Date of Review", "Date", "Review Date"],
            "User": ["User", "Username"],
            "Usefulness Vote": ["Usefulness Vote", "Helpful", "Helpful Votes"],
            "Total Votes": ["Total Votes", "Votes"],
            "User's Rating out of 10": ["User's Rating out of 10", "Rating", "User Rating"],
            "Review Title": ["Review Title", "Title"],
            "Review": ["Review", "Review Text", "Content", "Body"],
        }

        def pick(cols):
            for c in cols:
                if c in df.columns:
                    return c
            return None

        c_date   = pick(col_map["Date of Review"])
        c_user   = pick(col_map["User"])
        c_help   = pick(col_map["Usefulness Vote"])
        c_total  = pick(col_map["Total Votes"])
        c_rating = pick(col_map["User's Rating out of 10"])
        c_title  = pick(col_map["Review Title"])
        c_text   = pick(col_map["Review"])

        required = [c_user, c_help, c_total, c_rating]
        if any(c is None for c in required):
            print(f"⚠️ Skipping {movie_folder}: missing required columns.")
            continue

        reviews, votes = [], []
        added_rows, bad_rows = 0, 0

        for _, row in df.iterrows():
            try:
                username = clean_text(row.get(c_user, ""))
                if not username:
                    raise ValueError("missing username")

                helpful = safe_int(row.get(c_help))
                total = safe_int(row.get(c_total))
                rating = safe_int(row.get(c_rating))

                if helpful < 0 or total < 0 or helpful > total:
                    raise ValueError("invalid votes")
                if rating < 0 or rating > 10:
                    raise ValueError("rating out of range")

                # --- User handling ---
                if username not in user_index:
                    user_id = str(uuid.uuid4())
                    user = {
                        "user_id": user_id,
                        "username": username,
                        "email": f"{username}@inactive.com",
                        "hashed_password": "inactive_user",
                        "role": "member",
                        "status": "inactive",
                        "movies_reviewed": [movie_id],
                    }
                    inactive_users.append(user)
                    user_index[username] = user
                else:
                    user = user_index[username]
                    if movie_id not in user["movies_reviewed"]:
                        user["movies_reviewed"].append(movie_id)
                    user_id = user["user_id"]

                # --- Review entry ---
                review_id = str(uuid.uuid4())
                review_entry = {
                    "review_id": review_id,
                    "movie_id": movie_id,
                    "user_id": user_id,
                    "title": clean_text(row.get(c_title, "")),
                    "rating": rating,
                    "date": to_iso_date(row.get(c_date, "")) if c_date else "",
                    "text": clean_text(row.get(c_text, "")),
                    "usefulness": {"helpful": helpful, "total_votes": total},
                }
                reviews.append(review_entry)

                votes.append({
                    "review_id": review_id,
                    "helpful_votes": helpful,
                    "total_votes": total,
                    "helpfulness_ratio": round(helpful / total, 2) if total > 0 else 0
                })
                added_rows += 1

            except Exception:
                bad_rows += 1
                continue

        # Write per-movie review files
        reviews_out = os.path.join(REVIEWS_DIR, f"{movie_id}_reviews.json")
        votes_out = os.path.join(VOTES_DIR, f"{movie_id}_votes.json")
        with open(reviews_out, "w", encoding="utf-8") as f:
            json.dump(reviews, f, indent=4, ensure_ascii=False)
        with open(votes_out, "w", encoding="utf-8") as f:
            json.dump(votes, f, indent=4, ensure_ascii=False)

        print(f"✅ Processed {movie_folder}: {added_rows} reviews ({bad_rows} skipped)")

    # --- Save inactive users ---
    save_users(USERS_INACTIVE_PATH, inactive_users)
    print(f"\n🎉 Migration complete. Total inactive users: {len(inactive_users)}")

# ----------------------------------------
# Entrypoint
# ----------------------------------------
if __name__ == "__main__":
    migrate_all_movies()
