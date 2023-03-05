import datetime

import requests
import streamlit as st
import pandas as pd


class DataCollector:
    def __init__(self, search_query: str):
        self.api_base = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            'x-api-key': 'YOUR_API_KEY'
        }
        self.endpoint = f"{self.api_base}{search_query}&limit=10"
        self.data_set = self.get_data()
        # print(f"Length: {len(self.data_set)}")

    def get_data(self, offset=0, result=[]):
        url = f"{self.endpoint}&offset={offset}"
        # print(f"URL: {url}")
        response = requests.get(
            url=url, headers=self.headers
        )
        if response.ok:
            data = response.json()
            for d in data.get('data'):
                doi = None
                citation = None
                ext_details = d.get('externalIds')
                if ext_details and ext_details.get('DOI'):
                    doi = ext_details.get('DOI')
                if doi:
                    citation = DataCollector.get_citation(doi=doi)

                d_set = {
                    "TITLE": d.get('title'),
                    "DOI": doi,
                    "APA_CITE": citation,
                    "BibTex": d.get('citationStyles').get('bibtex'),
                    "SOURCE": d.get('url')
                }
                result.append(d_set)
            # result += data.get('data')

            if data.get('next'):
                # if offset >= 10:
                #     return result
                offset += 100
                self.get_data(offset=offset, result=result)
        return result

    @staticmethod
    def get_citation(doi, bib_format='apa'):
        base_url = f'https://citation.crosscite.org/format?doi={doi}&style={bib_format}&lang=en-US'
        response = requests.get(base_url)
        if response.ok:
            return response.text


if __name__ == '__main__':
    year = datetime.datetime.today().year
    YEARS = list(range(year, 1930, -1))
    FOS = [
        "Computer Science", "Medicine", "Chemistry", "Biology", "Materials Science", "Physics", "Geology", "Psychology",
        "Art", "History", "Geography", "Sociology", "Business", "Political Science", "Economics", "Philosophy",
        "Mathematics", "Engineering", "Environmental Science", "Agricultural and Food Sciences", "Education", "Law",
        "Linguistics"
    ]
    FIELDS = ["title", "externalIds", "citationStyles", "url"]
    st.set_page_config(
        page_title="Get Metadata",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://www.extremelycoolapp.com/help',
            'Report a bug': "https://www.extremelycoolapp.com/bug",
            'About': "# This is a header. This is an *extremely* cool app!"
        }
    )
    hide_menu_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
    st.markdown(hide_menu_style, unsafe_allow_html=True)
    search_string = st.text_input('Enter Your Search String')
    col1, col2 = st.columns(2)
    study_fields = col1.multiselect("Field of Study:", FOS)
    sub1, sub2, sub3 = col2.columns(3)
    from_year = sub1.selectbox("Search Year From : ", YEARS[::-1])
    to_year = sub2.selectbox("Search Year To: ", YEARS)
    pdf = sub3.selectbox("Has PDF:", [True, False])

    if search_string:
        query = f"/paper/search?query={search_string}"
        if from_year and to_year:
            query = f"{query}&year={from_year}-{to_year}"
        if pdf:
            query = f"{query}&openAccessPdf"
        if study_fields:
            query = f"{query}&fieldsOfStudy={','.join(study_fields)}"

        if FIELDS:
            query = f"{query}&fields={','.join(FIELDS)}"

        dc = DataCollector(search_query=query)

        st.markdown(f"Search Result Count: {len(dc.data_set)}")
        df = pd.DataFrame.from_dict(dc.data_set)
        st.dataframe(df)


