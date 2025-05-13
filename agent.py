import requests
from langchain_core.output_parsers import StrOutputParser
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import pdfplumber
from icecream import ic 
from dotenv import load_dotenv
from typing import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from templates import greet_template,greeting_template
import streamlit as st
from pydantic import BaseModel, Field
from langchain_core.documents import Document
from helper import llm, get_research_papers, check_link, categorise_links, jina_text_read, pdf_text_read
from langchain_google_genai import ChatGoogleGenerativeAI
from templates import template
from serpapi import GoogleSearch


class Greeting(BaseModel):
  """ Binary Score for whether the question is a greeting or not """
  binary_score:str=Field(
      ...,
      description='The question is a greeting  "yes" or "no"'
  )

greet_structured_llm=llm.with_structured_output(Greeting)

greet_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", greet_template),
        ("human", "User Query: {user_query} "),
    ]
)

greet_chain=greet_prompt | greet_structured_llm



greeting_template=ChatPromptTemplate.from_template(greeting_template)
greeting_chain=greeting_template | llm | StrOutputParser()


def respond (query):
    response = greeting_chain.invoke(query)

    return response

def ask_without_streaming(query):
    links, ref = get_research_papers(query)
    jina_links, pdf_links = categorise_links(links)

    jina_text = jina_text_read(jina_links)
    pdf_text = pdf_text_read(pdf_links)
    prompt = ChatPromptTemplate.from_template(template)
    answer_chain = prompt | llm | StrOutputParser()
    answer = answer_chain.invoke(
        {"user_query": query, "jina_text": jina_text, "pdf_text": pdf_text}
    )
    return answer



def ask(query):
   greet_score=greet_chain.invoke({'user_query':query})
   print(greet_score)
   if greet_score.binary_score=="yes":
       return respond(query)
   else:
      return ask_without_streaming(query)


while True:
  query=input('Enter your query: ').lower()
  if query=='exit' or query=='quit':

    break

  answer=ask(query)
  print(answer)
