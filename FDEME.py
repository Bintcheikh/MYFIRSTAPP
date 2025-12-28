import streamlit as st
import pandas as pd
import logging
from bs4 import BeautifulSoup as bs
from requests import get
import matplotlib.pyplot as plt
import seaborn as sns
import os
logging.basicConfig(level=logging.WARNING)

# ================= TITRE =================
st.markdown("<h1 style='text-align: center;'>MY FIRST APPLICATION</h1>", unsafe_allow_html=True)
st.markdown("Application de web scraping – Dakar-Auto (Véhicules, Motos & Locations)")

# ================= FONCTIONS =================
@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")

def load(dataframe, title, key):
    st.write(f"Dimensions : {dataframe.shape}")
    st.dataframe(dataframe)
    st.download_button(
        "Télécharger CSV",
        convert_df(dataframe),
        f"{title}.csv",
        "text/csv",
        key=key
    )

def get_proprietaire(container):
    txt = container.get_text(" ", strip=True)
    if "Par " in txt:
        return txt.split("Par ")[1].split("Appeler")[0].strip().title()
    return "Inconnu"

def get_adresse(container, type_):
    if type_ in ["moto", "location"]:
        adresse_tag = container.find("div", class_="col-12 entry-zone-address")
        if adresse_tag:
            return adresse_tag.text.strip()

    # fallback pour véhicules
    txt = container.get_text(" ", strip=True)
    for ville in ["Dakar", "Thiès", "Rufisque", "Pikine", "Guédiawaye"]:
        if ville in txt:
            return ville

    return "Non renseignée"

# ================= SCRAPING =================
def scrape_listing(url, type_):
    soup = bs(get(url).text, "html.parser")

    if type_ == "vehicle":
        containers = soup.find_all("div", class_="listings-cards__list-item mb-md-3 mb-3")
    else:
        containers = soup.find_all("div", class_="listing-card__content p-2")

    data = []

    for c in containers:
        try:
            # -------- TITRE --------
            title_tag = c.find("h2")
            if not title_tag:
                continue

            title = title_tag.text.split()
            marque = title[0]
            annee = int(title[-1]) if title[-1].isdigit() else None

            # -------- PRIX --------
            prix_tag = c.find("h3")
            prix = int(prix_tag.text.replace(" F CFA", "").replace("\u202f", "")) if prix_tag else None

            # -------- URL ANNONCE --------
            link_tag = c.find("a", href=True)
            url_annonce = "https://dakar-auto.com" + link_tag["href"] if link_tag else None

            # -------- PROPRIÉTAIRE --------
            proprietaire = get_proprietaire(c)
            
            #--------- adresse -----------
            adresse = get_adresse(c, type_)
            # -------- VEHICULE --------
            if type_ == "vehicle":
                infos = c.find_all("li")

                kilometrage = (
                    int(infos[1].text.replace(" km", "").replace("\u202f", ""))
                    if len(infos) > 1 else None
                )
                boite = infos[2].text if len(infos) > 2 else None
                carburant = infos[3].text if len(infos) > 3 else None

                data.append({
                    "marque": marque,
                    "annee": annee,
                    "prix": prix,
                    "kilometrage": kilometrage,
                    "boite": boite,
                    "carburant": carburant,
                    "adresse": adresse,
                    "proprietaire": proprietaire,
                    "url_annonce": url_annonce
                })

            # -------- MOTO --------
            elif type_ == "moto":
                infos = c.find_all("li")

                kilometrage = (
                    int(infos[1].text.replace(" km", "").replace("\u202f", ""))
                    if len(infos) > 1 else None
                )
                adresse_tag = c.find("div", class_="col-12 entry-zone-address")
                adresse = adresse_tag.text.strip() if adresse_tag else None

                data.append({
                    "marque": marque,
                    "annee": annee,
                    "prix": prix,
                    "kilometrage": kilometrage,
                    "adresse": adresse,
                    "proprietaire": proprietaire,
                    "url_annonce": url_annonce
                })

            # -------- LOCATION --------
            else:
                adresse_tag = c.find("div", class_="col-12 entry-zone-address")
                adresse = adresse_tag.text.strip() if adresse_tag else None

                owner_tag = c.find("span", class_="owner")
                proprietaire = owner_tag.text.strip() if owner_tag else "Inconnu"

                data.append({
                    "marque": marque,
                    "annee": annee,
                    "prix": prix,
                    "adresse": adresse,
                    "proprietaire": proprietaire,
                    "url_annonce": url_annonce
                })

        except Exception as e:
            logging.warning(f"Erreur scraping : {e}")

    return pd.DataFrame(data)
   #####
   

def load(df, title):
    st.markdown(f"### {title}")
    st.dataframe(df)

def plot_top5(df, title, color_palette):
    plt.figure(figsize=(6,4))
    top5 = df['marque'].value_counts().nlargest(5)
    sns.barplot(x=top5.index, y=top5.values, palette=color_palette)
    plt.title(title)
    plt.ylabel("Nombre d'annonces")
    for i, v in enumerate(top5.values):
        plt.text(i, v + 0.5, str(v), ha='center')
    st.pyplot(plt.gcf())
    plt.clf()

# ===================== Interface =====================
st.title("Véhicules - Motos - Location")

Choices = st.selectbox("Choisir une action", [
    "Scrape data using BeautifulSoup",
    "Download scraped data",
    "Dashboard of the data",
    "Evaluate the app"
])

Pages = st.number_input("Nombre de pages à scraper", min_value=1, max_value=20, value=3)

# ===================== Logique =====================

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
        Vehicles_data = pd.DataFrame()
        Motocycles_data = pd.DataFrame()
        Locations_data = pd.DataFrame()
        progress = st.progress(0)

        for p in range(1, Pages + 1):
            if scrape_vehicles:
                Vehicles_data = pd.concat([Vehicles_data, scrape_listing(f"https://dakar-auto.com/senegal/voitures-4?page={p}", "vehicle")], ignore_index=True)
            if scrape_motos:
                Motocycles_data = pd.concat([Motocycles_data, scrape_listing(f"https://dakar-auto.com/senegal/motos-and-scooters-3?page={p}", "moto")], ignore_index=True)
            if scrape_locations:
                Locations_data = pd.concat([Locations_data, scrape_listing(f"https://dakar-auto.com/senegal/location-de-voitures-19?page={p}", "location")], ignore_index=True)

            progress.progress(p / Pages)

        # Sauvegarde CSV si coché
        if scrape_vehicles:
            Vehicles_data.to_csv("Vehicles_data.csv", index=False)
            load(Vehicles_data, "Vehicles Data")
        if scrape_motos:
            Motocycles_data.to_csv("Motocycles_data.csv", index=False)
            load(Motocycles_data, "Motocycles Data")
        if scrape_locations:
            Locations_data.to_csv("Locations_data.csv", index=False)
            load(Locations_data, "Locations Data")

        st.success("Scraping terminé et fichiers CSV sauvegardés.")

elif Choices == "Download scraped data":
    if all(os.path.exists(f) for f in ['Vehicles_data.csv','Motocycles_data.csv','Locations_data.csv']):
        Vehicles = pd.read_csv('Vehicles_data.csv')
        Motocycles = pd.read_csv('Motocycles_data.csv')
        Locations = pd.read_csv('Locations_data.csv')
        load(Vehicles, "Vehicles Data")
        load(Motocycles, "Motocycles Data")
        load(Locations, "Locations Data")
    else:
        st.error("Les fichiers CSV n'existent pas. Veuillez d'abord scraper les données.")

elif Choices == "Dashboard of the data":
    if all(os.path.exists(f) for f in ['Vehicles_data.csv','Motocycles_data.csv','Locations_data.csv']):
        df1 = pd.read_csv('Vehicles_data.csv')
        df2 = pd.read_csv('Motocycles_data.csv')
        df3 = pd.read_csv('Locations_data.csv')

        col1, col2, col3 = st.columns(3)
        with col1:
            plot_top5(df1, "Top 5 Véhicules", "Greens")
        with col2:
            plot_top5(df2, "Top 5 Motos", "Blues")
        with col3:
            plot_top5(df3, "Top 5 Locations", "Reds")
    else:
        st.error("⚠️ Veuillez d'abord scraper les données pour voir le dashboard.")

else:  # Evaluate
    st.markdown("<h3 style='text-align: center;'>Donnez votre avis</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('[Kobo Evaluation Form](https://ee.kobotoolbox.org/x/bovbBGz7){:target="_blank"}', unsafe_allow_html=True)
    with col2:
        st.markdown('[Google Forms Evaluation](https://forms.gle/uFxkcoQAaU3f61LFA){:target="_blank"}', unsafe_allow_html=True)
