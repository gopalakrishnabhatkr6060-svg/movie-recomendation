import bz2
import os
import pickle
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import streamlit as st

# Setup Streamlit page
st.set_page_config(
    page_title="Movie Recommender System",
    page_icon="🎬",
    layout="wide"
)
st.title("🎬 Movie Recommender System")

# TMDB API Key
TMDB_API_KEY = "c97df0f6d9822ae08969416de7e699b9"

# Directory where this script and pkl files live
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Prepare TMDB session with retry and headers
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}
retries = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
session.mount("https://", HTTPAdapter(max_retries=retries))


@st.cache_data(show_spinner=False)
def fetch_poster(movie_id):
    """Fetch poster URL from TMDB. Return None on failure."""
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}
    try:
        response = session.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        path = data.get("poster_path")
        if path:
            return "https://image.tmdb.org/t/p/w500" + path
        return None
    except requests.exceptions.RequestException:
        return None


# Load data with caching so 184MB similarity matrix is not reloaded on every interaction
@st.cache_data
def load_data():
    dict_path = os.path.join(BASE_DIR, "movies_dict.pkl")
    sim_bz2_path = os.path.join(BASE_DIR, "similarity.pkl.bz2")
    sim_path = os.path.join(BASE_DIR, "similarity.pkl")

    with open(dict_path, "rb") as f:
        movies_dict = pickle.load(f)
    movies_df = pd.DataFrame(movies_dict)

    if os.path.exists(sim_bz2_path):
        with bz2.BZ2File(sim_bz2_path, "rb") as f:
            sim_matrix = pickle.load(f)
    else:
        with open(sim_path, "rb") as f:
            sim_matrix = pickle.load(f)

    return movies_df, sim_matrix


movies, similarity = load_data()


def recommend(movie):
    matches = movies[movies["title"] == movie]
    if matches.empty:
        return [], []

    movie_index = matches.index[0]
    distances = similarity[movie_index]

    # Get top 5 recommendations (skip index 0, which is the movie itself)
    movies_list = sorted(enumerate(distances), key=lambda x: x[1], reverse=True)[1:6]

    titles, posters = [], []
    for idx, _ in movies_list:
        movie_id = movies.iloc[idx].movie_id
        titles.append(movies.iloc[idx].title)
        posters.append(fetch_poster(movie_id))
    return titles, posters


# UI: movie selector and Recommend button
selected_movie = st.selectbox("Select a movie", movies["title"].values)

if st.button("Recommend", type="primary"):
    with st.spinner("Finding recommendations..."):
        names, posters = recommend(selected_movie)

    if not names:
        st.error("No recommendations found.")
    else:
        cols = st.columns(len(names))
        for i in range(len(names)):
            with cols[i]:
                st.markdown(f"**{names[i]}**")
                if posters[i]:
                    st.image(posters[i], use_container_width=True)
                else:
                    st.caption("Poster unavailable")
