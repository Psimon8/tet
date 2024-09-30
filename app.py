import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import google.auth.transport.requests
import os
import pickle
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import re

# Définir le fichier client_secrets.json contenant l'ID client OAuth 2.0
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# Fonction pour gérer l'authentification OAuth 2.0
def authenticate_user():
    # Création d'un objet Flow pour gérer le flux OAuth 2.0
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES,
        redirect_uri="http://localhost:8501")  # URL de redirection pour Streamlit local

    # Générer l'URL d'authentification OAuth 2.0
    authorization_url, state = flow.authorization_url(prompt='consent')

    # Afficher le lien pour l'utilisateur pour qu'il se connecte via Google
    st.write("Veuillez vous authentifier via Google pour continuer :")
    st.markdown(f"[Se connecter via Google]({authorization_url})")

    # Récupérer le code d'autorisation après la connexion
    code = st.text_input("Entrez le code d'autorisation ici")

    if code:
        # Échanger le code d'autorisation contre un jeton d'accès
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Sauvegarder les informations d'authentification pour les réutiliser
        with open('token.pkl', 'wb') as token_file:
            pickle.dump(credentials, token_file)

        st.success("Authentification réussie !")

# Fonction pour charger les credentials sauvegardés
def load_credentials():
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token_file:
            credentials = pickle.load(token_file)
            return credentials
    return None

# Fonction pour exécuter la requête vers Google Search Console
def execute_request(service, property_uri, request):
    return service.searchanalytics().query(siteUrl=property_uri, body=request).execute()

# Interface Streamlit
def main():
    st.title("Analyse de Cannibalisation Google Search Console")

    # Authentifier l'utilisateur si ce n'est pas déjà fait
    credentials = load_credentials()
    if not credentials:
        authenticate_user()
        return

    # Charger l'API Search Console
    service = build('searchconsole', 'v1', credentials=credentials)

    # Sélecteur de dates pour la période à analyser
    start_date = st.date_input('Date de début', value=datetime.today() - timedelta(days=90))
    end_date = st.date_input('Date de fin', value=datetime.today())

    # Saisie de l'URL du site
    site_url = st.text_input('Entrez l\'URL du site', 'https://example.com')

    # Saisie du filtre device
    device_category = st.selectbox('Sélectionnez la catégorie de device', ['Tous', 'MOBILE', 'DESKTOP', 'TABLET'])

    # Champ pour la regex des mots-clés à exclure
    exclude_regex = st.text_input('Regex des mots-clés à exclure (optionnel)')

    if st.button("Analyser les données"):
        # Préparation de la requête
        request = {
            'startDate': start_date.strftime("%Y-%m-%d"),
            'endDate': end_date.strftime("%Y-%m-%d"),
            'dimensions': ['page', 'query'],
            'rowLimit': 25000
        }

        # Appliquer un filtre sur le device si sélectionné
        if device_category != 'Tous':
            request['dimensionFilterGroups'] = [{'filters': [{'dimension': 'device', 'expression': device_category}]}]

        # Exécution de la requête
        response = execute_request(service, site_url, request)

        # Traiter les données reçues
        scDict = defaultdict(list)
        for row in response.get('rows', []):
            scDict['page'].append(row['keys'][0])
            scDict['query'].append(row['keys'][1])
            scDict['clicks'].append(row['clicks'])
            scDict['ctr'].append(row['ctr'] * 100)  # Convertir en pourcentage
            scDict['impressions'].append(row['impressions'])
            scDict['position'].append(row['position'])

        df = pd.DataFrame(data=scDict)
        df['clicks'] = df['clicks'].astype('int')
        df['impressions'] = df['impressions'].astype('int')
        df['position'] = df['position'].round(2)
        df.sort_values('clicks', inplace=True, ascending=False)

        # Filtrer les mots-clés avec la regex si elle est fournie
        if exclude_regex:
            df = df[~df['query'].str.contains(exclude_regex, regex=True, na=False)]
        
        # Afficher les résultats dans un tableau
        st.write("Données de la Search Console (après filtrage) :")
        st.dataframe(df)

        # Ajouter un bouton de téléchargement
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Télécharger les résultats", data=csv, file_name="search_console_data.csv", mime='text/csv')

if __name__ == "__main__":
    main()
