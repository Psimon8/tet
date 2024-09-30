import streamlit as st
import pandas as pd
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Authentification à l'API Google Search Console
CLIENT_SECRETS_FILE = "client_secrets.json"  # Assurez-vous que ce fichier est dans le même dossier que votre script
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
credentials = service_account.Credentials.from_service_account_file(CLIENT_SECRETS_FILE, scopes=SCOPES)

def get_search_console_service():
    return build('searchconsole', 'v1', credentials=credentials)

# Fonction pour exécuter la requête vers l'API Google Search Console
def execute_request(service, property_uri, request):
    return service.searchanalytics().query(siteUrl=property_uri, body=request).execute()

# Fonction pour récupérer les meta titres et descriptions
def get_meta(url):
    try:
        page = requests.get(url, timeout=5)
        soup = BeautifulSoup(page.content, 'html.parser')
        title = soup.find('title').get_text() if soup.find('title') else 'No Title'
        meta = soup.select('meta[name="description"]')
        meta_description = meta[0].attrs["content"] if meta else 'No Meta Description'
        return title, meta_description
    except Exception as e:
        return 'Error Fetching', 'Error Fetching'

# Fonction principale de cannibalisation
def process_cannibalization(df):
    SERP_results = 8  # Limite de position pour la première page
    branded_queries = 'brand|vrand|b rand...'  # Remplacer par vos termes de marque

    # Filtrage des positions hors première page
    df_canibalized = df[df['position'] > SERP_results]
    
    # Exclure les requêtes contenant des termes de marque
    df_canibalized = df_canibalized[~df_canibalized['query'].str.contains(branded_queries, regex=True)]
    
    # Conserver les requêtes dupliquées (cannibalisation)
    df_canibalized = df_canibalized[df_canibalized.duplicated(subset=['query'], keep=False)]
    
    # Réinitialiser l'index
    df_canibalized.set_index(['query'], inplace=True)
    df_canibalized.sort_index(inplace=True)
    df_canibalized.reset_index(inplace=True)

    # Ajouter les titres et meta descriptions
    df_canibalized['title'], df_canibalized['meta'] = zip(*df_canibalized['page'].apply(get_meta))
    
    return df_canibalized

# Interface Streamlit
def main():
    st.title('Analyse de Cannibalisation Google Search Console')

    # Sélection des dates
    start_date = st.date_input('Date de début', value=datetime.date.today() - datetime.timedelta(days=90))
    end_date = st.date_input('Date de fin', value=datetime.date.today())

    # Saisie de l'URL du site
    site = st.text_input('Entrez l\'URL du site', 'https://example.com')

    # Saisie du filtre par device
    device_category = st.selectbox('Sélectionnez la catégorie de device', ['Tous', 'MOBILE', 'DESKTOP', 'TABLET'])

    # Bouton pour exécuter la requête
    if st.button('Analyser les données'):
        request = {
            'startDate': start_date.strftime("%Y-%m-%d"),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'dimensions': ['page', 'query'],
            'rowLimit': 25000  # Limite de 25.000 URLs
        }

        # Appliquer le filtre device
        if device_category != 'Tous':
            request['dimensionFilterGroups'] = [{'filters': [{'dimension': 'device', 'expression': device_category}]}]

        # Exécuter la requête
        webmasters_service = get_search_console_service()
        response = execute_request(webmasters_service, site, request)

        # Traiter les résultats
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

        # Afficher les résultats dans un tableau
        st.write("Données de la Search Console :")
        st.dataframe(df)

        # Traiter la cannibalisation
        df_cannibalized = process_cannibalization(df)

        # Afficher le DataFrame des résultats cannibalisés
        st.write("Résultats de cannibalisation :")
        st.dataframe(df_cannibalized)

        # Bouton de téléchargement
        csv = df_cannibalized.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Télécharger les données",
            data=csv,
            file_name='cannibalisation_data.csv',
            mime='text/csv',
        )

if __name__ == "__main__":
    main()
