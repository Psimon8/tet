import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import pickle
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

# Définir le fichier client_secrets.json contenant l'ID client OAuth 2.0
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# Fonction pour gérer l'authentification OAuth 2.0
def authenticate_user():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES,
        redirect_uri="http://localhost:8501")
    authorization_url, state = flow.authorization_url(prompt='consent')
    st.write("Veuillez vous authentifier via Google pour continuer :")
    st.markdown(f"[Se connecter via Google]({authorization_url})")
    code = st.text_input("Entrez le code d'autorisation ici")
    if code:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        with open('token.pkl', 'wb') as token_file:
            pickle.dump(credentials, token_file)
        st.success("Authentification réussie !")

def load_credentials():
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token_file:
            credentials = pickle.load(token_file)
            return credentials
    return None

# Fonction avec timeout
def execute_request(service, property_uri, request, timeout=60):
    try:
        return service.searchanalytics().query(siteUrl=property_uri, body=request).execute(timeout=timeout)
    except HttpError as error:
        st.error(f"Une erreur s'est produite lors de l'exécution de la requête : {error}")
    except Exception as e:
        st.error(f"Erreur inattendue : {str(e)}")

# Interface Streamlit
def main():
    st.title("Analyse de Cannibalisation Google Search Console")
    credentials = load_credentials()
    if not credentials:
        authenticate_user()
        return

    service = build('searchconsole', 'v1', credentials=credentials)
    start_date = st.date_input('Date de début', value=datetime.today() - timedelta(days=90))
    end_date = st.date_input('Date de fin', value=datetime.today())
    site_url = st.text_input('Entrez l\'URL du site', 'https://example.com')
    device_category = st.selectbox('Sélectionnez la catégorie de device', ['Tous', 'MOBILE', 'DESKTOP', 'TABLET'])
    exclude_regex = st.text_input('Regex des mots-clés à exclure (optionnel)')

    if st.button("Analyser les données"):
        request = {
            'startDate': start_date.strftime("%Y-%m-%d"),
            'endDate': end_date.strftime("%Y-%m-%d"),
            'dimensions': ['page', 'query'],
            'rowLimit': 1000  # Limiter à 1000 lignes pour éviter un timeout
        }

        if device_category != 'Tous':
            request['dimensionFilterGroups'] = [{'filters': [{'dimension': 'device', 'expression': device_category}]}]

        response = execute_request(service, site_url, request)

        if response:
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

            if exclude_regex:
                df = df[~df['query'].str.contains(exclude_regex, regex=True, na=False)]

            st.write("Données de la Search Console (après filtrage) :")
            st.dataframe(df)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Télécharger les résultats", data=csv, file_name="search_console_data.csv", mime='text/csv')

if __name__ == "__main__":
    main()
