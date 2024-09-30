
# Fichier : app.py
import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle
import os
import pandas as pd
from datetime import datetime, timedelta

# Configuration des paramètres OAuth 2.0
CLIENT_SECRETS_FILE = "client_secrets.json"  # Remplace avec ton fichier JSON de Client ID
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# Fonction pour gérer l'authentification OAuth 2.0
def authenticate_user():
    if 'credentials' not in st.session_state:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, 
            scopes=SCOPES,
            redirect_uri="http://localhost:8501")

        auth_url, _ = flow.authorization_url(prompt='consent')
        st.write("Veuillez vous authentifier via Google pour continuer :")
        st.markdown(f"[Se connecter via Google]({auth_url})")
        code = st.text_input('Code d\'autorisation')

        if code:
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Stocker les informations d'authentification dans la session
            st.session_state.credentials = credentials

# Fonction pour créer une instance du service Google Search Console
def get_search_console_service():
    credentials = st.session_state.credentials
    if credentials:
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

    # Authentification de l'utilisateur
    if 'credentials' not in st.session_state:
        authenticate_user()
    else:
        # Si l'utilisateur est authentifié, lui permettre de saisir l'URL du site
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
