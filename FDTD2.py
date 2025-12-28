import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from bs4 import BeautifulSoup as bs
from requests import get
import logging
import os

logging.basicConfig(level=logging.WARNING)
sns.set_style("whitegrid")  # Style seaborn

# ================= TITRE =================
st.markdown("<h1 style='text-align: center;'>MY BEST DATA APP</h1>", unsafe_allow_html=True)
st.markdown("Application de web scraping – Dakar-Auto (Véhicules, Motos & Locations)")

# ================= FONCTIONS =================
@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")

def load(dataframe, title, key1, key2):
    st.write(f"Dimensions : {dataframe.shape}")
    st.dataframe(dataframe)
    st.download_button(
        "Télécharger CSV",
        convert_df(dataframe),
        f"{title}.csv",
        "text/csv",
        key=key2
    )

def get_proprietaire(container):
    txt = container.get_text(" ", strip=True)
    if "Par " in txt:
        return txt.split("Par ")[1].split("Appeler")[0].strip().title()
    return "Inconnu"

def get_adresse(container, type_):
    if type_ in ["vehicle","moto", "location"]:
        adresse_tag = container.find("div", class_="col-12 entry-zone-address")
        if adresse_tag:
            return adresse_tag.text.strip()

def scrape_listing(url, type_):
    soup = bs(get(url).text, "html.parser")

    if type_ == "vehicle":
        containers = soup.find_all("div", class_="listings-cards__list-item mb-md-3 mb-3")
    else:
        containers = soup.find_all("div", class_="listing-card__content p-2")

    data = []
    for c in containers:
        try:
            title = c.find("h2").text.split()
            marque = title[0]
            annee = int(title[-1])
            prix = int(c.find("h3").text.replace(" F CFA", "").replace("\u202f", ""))
            proprietaire = get_proprietaire(c)
            adresse = get_adresse(c, type_)

            if type_ == "vehicle":
                infos = c.find_all("li")
                kilometrage = int(infos[1].text.replace(" km", "").replace("\u202f", ""))
                boite = infos[2].text
                carburant = infos[3].text
                data.append({
                    "marque": marque,
                    "annee": annee,
                    "prix": prix,
                    "adresse": adresse,
                    "kilometrage": kilometrage,
                    "boite": boite,
                    "carburant": carburant,
                    "proprietaire": proprietaire
                })

            elif type_ == "moto":
                infos = c.find_all("li")
                kilometrage = int(infos[1].text.replace(" km", "").replace("\u202f", ""))
                data.append({
                    "marque": marque,
                    "annee": annee,
                    "prix": prix,
                    "adresse": adresse,
                    "kilometrage": kilometrage,
                    "proprietaire": proprietaire
                })

            else:  # location
                proprietaire_tag = c.find("span", class_="owner")
                proprietaire = proprietaire_tag.text.strip() if proprietaire_tag else "Inconnu"
                data.append({
                    "marque": marque,
                    "annee": annee,
                    "prix": prix,
                    "adresse": adresse,
                    "proprietaire": proprietaire
                })

        except Exception as e:
            logging.warning(f"Erreur scraping : {e}")

    return pd.DataFrame(data)

# ================= SIDEBAR =================
st.sidebar.header("Paramètres")
Pages = st.sidebar.selectbox("Nombre de pages à scraper", list(np.arange(2, 50)))
Choices = st.sidebar.selectbox("Options", [
    "Scrape data using BeautifulSoup",
    "Download scraped data",
    "Dashboard of the data",
    "Evaluate the App"
])

# ================= LOGIQUE =================
if Choices == "Scrape data using BeautifulSoup":

    st.subheader("Choisissez les données à scraper")

    col1, col2, col3 = st.columns(3)
    with col1:
        scrape_vehicles = st.checkbox("Véhicules")
    with col2:
        scrape_motos = st.checkbox("Motos")
    with col3:
        scrape_locations = st.checkbox("Locations")

    if not (scrape_vehicles or scrape_motos or scrape_locations):
        st.info("Veuillez sélectionner au moins une catégorie.")
        st.stop()

    if st.button("▶ Lancer le scraping"):

        progress = st.progress(0.0)
        Vehicles_df = pd.DataFrame()
        Motocycles_df = pd.DataFrame()
        Locations_df = pd.DataFrame()

        for p in range(1, Pages + 1):

            if scrape_vehicles:
                Vehicles_df = pd.concat([Vehicles_df,
                    scrape_listing(f"https://dakar-auto.com/senegal/voitures-4?page={p}", "vehicle")],
                    ignore_index=True
                )

            if scrape_motos:
                Motocycles_df = pd.concat([Motocycles_df,
                    scrape_listing(f"https://dakar-auto.com/senegal/motos-and-scooters-3?page={p}", "moto")],
                    ignore_index=True
                )

            if scrape_locations:
                Locations_df = pd.concat([Locations_df,
                    scrape_listing(f"https://dakar-auto.com/senegal/location-de-voitures-19?page={p}", "location")],
                    ignore_index=True
                )

            progress.progress(p / Pages)

        if scrape_vehicles:
            Vehicles_df.to_csv("Vehicles_data.csv", index=False)
            load(Vehicles_df, "Vehicles_data", "1", "101")

        if scrape_motos:
            Motocycles_df.to_csv("Motocycles_data.csv", index=False)
            load(Motocycles_df, "Motocycles_data", "2", "102")

        if scrape_locations:
            Locations_df.to_csv("Locations_data.csv", index=False)
            load(Locations_df, "Locations_data", "3", "103")

elif Choices == "Download scraped data":

    files = ["Vehicles_data.csv", "Motocycles_data.csv", "Locations_data.csv"]
    if any(os.path.exists(f) for f in files):
        if os.path.exists("Vehicles_data.csv"):
            load(pd.read_csv("Vehicles_data.csv"), "Vehicles_data", "1", "101")
        if os.path.exists("Motocycles_data.csv"):
            load(pd.read_csv("Motocycles_data.csv"), "Motocycles_data", "2", "102")
        if os.path.exists("Locations_data.csv"):
            load(pd.read_csv("Locations_data.csv"), "Locations_data", "3", "103")
    else:
        st.error("Aucune donnée trouvée. Veuillez scraper d'abord.")

elif Choices == "Dashboard of the data":

    if os.path.exists("Vehicles_data.csv"):
        df1 = pd.read_csv("Vehicles_data.csv")

        # Nettoyage et conversion
        df1['prix'] = pd.to_numeric(df1['prix'], errors='coerce')
        df1['annee'] = pd.to_numeric(df1['annee'], errors='coerce')
        df1 = df1.dropna(subset=['prix', 'annee'])

        # Top 10 marques
        st.subheader("Top 10 marques")
        plt.figure(figsize=(10,6))
        sns.countplot(y="marque", data=df1, order=df1['marque'].value_counts().index[:10], palette="viridis")
        plt.title("Top 10 des marques de véhicules")
        plt.xlabel("Nombre de véhicules")
        plt.ylabel("Marque")
        st.pyplot(plt.gcf())

        # Prix moyen par année
        st.subheader("Prix moyen par année")
        plt.figure(figsize=(10,6))
        df1.groupby("annee")["prix"].mean().plot(kind='bar', color="orange")
        plt.title("Prix moyen des véhicules par année")
        plt.xlabel("Année")
        plt.ylabel("Prix moyen (F CFA)")
        plt.xticks(rotation=45)
        st.pyplot(plt.gcf())

    else:
        st.error("Veuillez scraper au moins les véhicules pour voir le dashboard.")

else:  # Evaluate
    st.markdown("<h3 style='text-align: center;'>Give your Feedback</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("[Kobo Evaluation Form](https://ee.kobotoolbox.org/x/sv3Wset7)")
    with col2:
        st.markdown("[Google Forms Evaluation](https://forms.gle/uFxkcoQAaU3f61LFA)")
