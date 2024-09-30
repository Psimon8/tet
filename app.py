# Fichier : app.py
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime, timedelta

# Paramètres d'authentification
# Remplacer par ton fichier de clés JSON généré par Google Cloud
SERVICE_ACCOUNT_FILE = 'service_account.json'
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# Authentification à l'API Search Console
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Créer une instance du service API
def get_search_console_service():
    return build('searchconsole', 'v1', credentials=credentials)

# Obtenir les données des 3 derniers mois
def get_search_console_data(site_url):
    service = get_search_console_service()

    # Calculer les dates de début et de fin (3 derniers mois)
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=90)

    # Effectuer une requête sur l'API Search Console
    request = {
        'startDate': str(start_date),
        'endDate': str(end_date),
        'dimensions': ['query'],
        'rowLimit': 1000,  # Limite du nombre de mots-clés
        'fields': 'rows/clicks,rows/keys'
    }

    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    return response.get('rows', [])

# Extraire les mots-clés avec le plus de clics
def get_top_keywords(data, top_n=5):
    df = pd.DataFrame(data)
    df['clicks'] = df['clicks'].astype(int)
    df = df.sort_values(by='clicks', ascending=False)
    return df.head(top_n)

# Interface Streamlit
def main():
    st.title('Top 5 Mots-Clés sur Google Search Console')

    # URL du site à analyser (remplacer par l'URL de ton site)
    site_url = st.text_input('Entrez l\'URL du site', 'https://example.com')

    if st.button('Afficher les résultats'):
        st.write(f'Données des 3 derniers mois pour le site: {site_url}')
        
        # Récupérer les données de la Search Console
        data = get_search_console_data(site_url)

        if data:
            # Trier et afficher les 5 mots-clés avec le plus de clics
            top_keywords = get_top_keywords(data)
            st.dataframe(top_keywords)
        else:
            st.write("Aucune donnée trouvée")

if __name__ == "__main__":
    main()
