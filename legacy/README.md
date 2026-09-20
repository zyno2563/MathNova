# Legacy Streamlit interface

`streamlit_app.py` is the original single-file Streamlit UI that MathNova
used before the web architecture (FastAPI backend + HTML/CSS/JS frontend)
replaced it.

It is kept for reference only:

* **Nothing in the shipped app imports it.** `backend/` and `frontend/`
  have no Streamlit dependency, and `requirements.txt` does not install
  Streamlit.
* It is excluded from the Docker image (see `.dockerignore`).
* Every calculation it performed is available through the REST API and
  the new frontend.

To run it anyway you would need Streamlit installed separately:

```bash
pip install streamlit plotly
streamlit run legacy/streamlit_app.py
```

To delete it for good:

```bash
git rm -r legacy visualization
```

(`visualization/plots.py` builds Plotly figures for this interface only —
the web frontend draws its own charts from the raw series the API
returns.)
