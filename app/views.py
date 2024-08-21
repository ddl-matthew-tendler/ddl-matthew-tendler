import pandas as pd
import plotly
import plotly.express as px
from flask import render_template

from app import app

@app.route("/")
def homepage():
    df = pd.read_excel("/mnt/data/Dexcom_Readings/DexcomG8Domino.xlsx")
    fig = px.line(df, x='Timestamp', y='Glucose Level (mg/dL)', color='Alert')
    graphJSON = fig.to_json()
    return render_template("dashboard.html", graphJSON=graphJSON)
