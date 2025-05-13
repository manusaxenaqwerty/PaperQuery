import requests
from langchain_core.output_parsers import StrOutputParser
import fitz
import aiohttp
import asyncio
from langchain_groq import ChatGroq
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

from icecream import ic 
from dotenv import load_dotenv
from templates import greet_template
from langchain_core.prompts import ChatPromptTemplate

import streamlit as st

from langchain_core.documents import Document

from langchain_google_genai import ChatGoogleGenerativeAI
from templates import template
from serpapi import GoogleSearch
from pydantic import BaseModel, Field

load_dotenv()
# ic.disable()

grader_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
    api_key=st.secrets["GROQ_API_KEY"],
)

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.1,
    api_key=st.secrets["GOOGLE_API_KEY"],
    stream=True,
)


def get_research_papers(query, num: int = 20):

    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": st.secrets["SERPAPI_KEY"],
        "num": num,
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    organic_results = results["organic_results"]

    links = []
    ref = {}

    for result in organic_results:
        try:
            if 'resources' in result and result['resources'] and 'link' in result['resources'][0]:
              links.append(result['resources'][0]['link'])
              ref[result["title"]] = result['resources'][0]['link']
            else:
              links.append(result["link"])
              ref[result["title"]] = result["link"]

            

        except:
            pass
    ic(ref)
    return links, ref



def check_link(link):
    """Check if the link points to a PDF or categorize as Jina link."""
    try:
       
        if "https://books.google.com/" in link:
            pass

        response = requests.head(link, timeout=10, allow_redirects=True)
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/pdf" in content_type:
            return "pdf", link
    except requests.RequestException:
        pass  

    return "jina", link


def categorise_links(links):
    """Categorize links into PDF links and Jina links using parallel requests."""
    jina_links = []
    pdf_links = []

    with ThreadPoolExecutor(
        max_workers=10
    ) as executor:  # 10 threads for parallel execution
        futures = {executor.submit(check_link, link): link for link in links}

        for future in as_completed(futures):
            result_type, link = future.result()
            if result_type == "pdf":
                pdf_links.append(link)
            elif result_type == "jina":
                jina_links.append("https://r.jina.ai/" + link)
    ic(jina_links, pdf_links)
    return jina_links, pdf_links


def fetch_link_content(link):
    """Fetch the content of a link and return a Document."""
    try:
        response = requests.get(link, timeout=5)  
        response.raise_for_status()  
        text = response.text
        return Document(page_content=text, metadata={"source": link})
    except requests.RequestException as e:
        pass
        return None  


def jina_text_read(jina_links):
    """Fetch text content from multiple links in parallel and return as Documents."""
    jina_text = []

    with ThreadPoolExecutor(max_workers=10) as executor:  # Adjust max_workers as needed
        futures = {
            executor.submit(fetch_link_content, link): link for link in jina_links
        }

        for future in as_completed(futures):
            document = future.result()
            if document is not None:  # Add only successfully fetched documents
                jina_text.append(document)
    ic(jina_text)
    return jina_text




async def extract_text_from_pdf_url(link, session):
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
    async with session.get(link,headers=headers) as response:
        response.raise_for_status()  
        pdf_content = await response.read()

    
    doc = fitz.open(stream=pdf_content, filetype="pdf")
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)  
        text += page.get_text()  
    return text


async def pdf_text_read(pdf_links):
    async with aiohttp.ClientSession() as session:
        tasks = [extract_text_from_pdf_url(link, session) for link in pdf_links]
        texts = await asyncio.gather(*tasks)
        return texts


class Greeting(BaseModel):
  """ Binary Score for whether the question is a greeting or not """
  binary_score:str=Field(
      ...,
      description='The question is a greeting  "yes" or "no"'
  )

greet_structured_llm=grader_llm.with_structured_output(Greeting)

greet_check_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", greet_template),
        ("human", "User Query: {user_query} "),
    ]
)

greet_check_chain=greet_check_prompt | greet_structured_llm





def ask(query):
    links, ref = get_research_papers(query)
    jina_links, pdf_links = categorise_links(links)

    jina_text = jina_text_read(jina_links)
    

        
    return ref,jina_text,pdf_links 


   
   
def llm_call(query, jina_text, pdf_text):
    prompt = ChatPromptTemplate.from_template(template)
    answer_chain = prompt | llm | StrOutputParser()
    for chunk in answer_chain.stream(
        {"user_query": query, "jina_text": jina_text, "pdf_text": pdf_text}
    ):
        yield chunk

