import datetime
import os
from io import BytesIO

import requests
import streamlit as st
import pandas as pd


class GoogleScholarData:
    def __init__(self, author_unique_id):
        self.api_key = os.getenv('GOOGLE_API')
        base_url = 'https://serpapi.com/search'
        self.url = f"{base_url}?engine=google_scholar_author&author_id={author_unique_id}&hl=en&start=0&num=100"

    def get_paper_data(self, url=None, articles=[]):
        search_url = url if url else self.url
        search_url = f"{search_url}&api_key={self.api_key}"
        response = requests.get(search_url)

        if response.ok:
            data = response.json()
            articles += data.get('articles')
            if data.get('serpapi_pagination'):
                next_page = data.get('serpapi_pagination').get('next')
                return self.get_paper_data(url=next_page, articles=articles)
        return articles


class SemanticScholarData:
    def __init__(self, search_query: str):
        self.api_base = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            'x-api-key': os.getenv('SEMANTIC_API')
        }
        self.endpoint = f"{self.api_base}{search_query}&limit=100"

    def generate_data(self, offset=0) -> dict:
        url = f"{self.endpoint}&offset={offset}"
        response = requests.get(url=url, headers=self.headers)
        if response.ok:
            data = response.json()
            for d in data.get('data'):
                doi = None
                citation = None
                ext_details = d.get('externalIds')
                if ext_details and ext_details.get('DOI'):
                    doi = ext_details.get('DOI')
                if doi:
                    citation = SemanticScholarData.get_citation(doi=doi)

                d_set = {
                    "TITLE": d.get('title'),
                    "DOI": doi,
                    "CITATION_COUNT": d.get('citationCount'),
                    "REFERENCE_COUNT": d.get('referenceCount'),
                    "YEAR": d.get('year'),
                    "APA_CITE": citation,
                    "BibTex": d.get('citationStyles').get('bibtex'),
                    "SOURCE": d.get('url'),
                }
                yield d_set

            if data.get('next'):
                if offset < 10000:
                    yield from self.generate_data(offset=offset + 100)

    @staticmethod
    def get_citation(doi, bib_format='apa'):
        base_url = f'https://citation.crosscite.org/format?doi={doi}&style={bib_format}&lang=en-US'
        response = requests.get(base_url)
        if response.ok:
            return response.text


def to_excel(data_frame):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    data_frame.to_excel(writer, index=False, sheet_name='Sheet1')
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    format1 = workbook.add_format({'num_format': '0.00'})
    worksheet.set_column('A:A', None, format1)
    writer.save()
    processed_data = output.getvalue()
    return processed_data


if __name__ == '__main__':
    year = datetime.datetime.today().year
    YEARS = list(range(year, 1930, -1))
    LIMIT = list(range(10, 1000, 30))
    LIMIT.insert(0, "ALL")
    FOS = [
        "Computer Science", "Medicine", "Chemistry", "Biology", "Materials Science", "Physics", "Geology", "Psychology",
        "Art", "History", "Geography", "Sociology", "Business", "Political Science", "Economics", "Philosophy",
        "Mathematics", "Engineering", "Environmental Science", "Agricultural and Food Sciences", "Education", "Law",
        "Linguistics"
    ]
    FIELDS = ["title", "externalIds", "citationStyles", "url", "citationCount", "referenceCount", "year"]
    st.set_page_config(
        page_title="Get Metadata",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    hide_menu_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
    st.markdown(hide_menu_style, unsafe_allow_html=True)
    # display a placeholder
    my_placeholder = st.empty()
    dow1, dow2 = st.columns(2)
    with st.sidebar:
        data_source = st.radio(
            "Choose a Data Source",
            ("Semantic Scholar", "Google Scholar")
        )
        if data_source == 'Semantic Scholar':
            form = st.sidebar.form("Fill the Form:")
            search_string = form.text_input('Enter Your Search String')
            # submitted = form.form_submit_button("Submit")
            col1, col2 = form.columns(2)
            study_fields = col1.multiselect("Field of Study:", FOS)
            pdf = col2.selectbox("Has PDF:", [True, False])
            from_year = col1.selectbox("Search Year From : ", YEARS[::-1])
            to_year = col2.selectbox("Search Year To: ", YEARS)
            limit = col1.selectbox("Display Top: ", LIMIT)
            # Every form must have a submit button.
            submitted = form.form_submit_button("Submit")

            if submitted:
                query = f"/paper/search?query={search_string}"
                if from_year and to_year:
                    query = f"{query}&year={from_year}-{to_year}"
                if pdf:
                    query = f"{query}&openAccessPdf"
                if study_fields:
                    query = f"{query}&fieldsOfStudy={','.join(study_fields)}"

                if FIELDS:
                    query = f"{query}&fields={','.join(FIELDS)}"

                data_list = []
                df = None
                dc = SemanticScholarData(search_query=query)
                for data_set in dc.generate_data():
                    data_list.append(data_set)
                    if data_list:
                        df = pd.DataFrame.from_dict(data_list)
                        my_placeholder.dataframe(df)
                    if limit != 'ALL' and len(data_list) >= limit:
                        break
                st.balloons()
                if not df.empty:
                    dow1.download_button(
                        label="📥 Download CSV",
                        data=df.to_csv(index=False),
                        mime='text/csv',
                        file_name='GoogleScholarReport.csv'
                    )
                    dow2.download_button(
                        label="📥 Download XLSX",
                        data=to_excel(df),
                        mime='application/vnd.ms-excel',
                        file_name='GoogleScholarReport.xlsx'
                    )

        elif data_source == 'Google Scholar':
            form = st.sidebar.form("Fill the Form:")
            author_id = form.text_input('Enter Author ID:')
            submitted = form.form_submit_button("Submit")
            if submitted:
                data_list = GoogleScholarData(author_unique_id=author_id).get_paper_data()
                if data_list:
                    df = pd.DataFrame.from_dict(data_list)
                    df.drop(['citation_id', 'cited_by'], axis=1, inplace=True)
                    field_order = ['authors', 'year', 'title', 'publication', 'link']
                    new_df = df.reindex(columns=field_order)
                    my_placeholder.dataframe(new_df)
                    st.balloons()
                    csv_df = new_df.drop(['link'], axis=1)
                    dow1.download_button(
                        label="📥 Download CSV",
                        data=csv_df.to_csv(index=False),
                        mime='text/csv',
                        file_name='GoogleScholarReport.csv'
                    )
                    dow2.download_button(
                        label="📥 Download XLSX",
                        data=to_excel(new_df),
                        mime='application/vnd.ms-excel',
                        file_name='GoogleScholarReport.xlsx'
                    )
