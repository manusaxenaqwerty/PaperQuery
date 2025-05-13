import streamlit as st
from helper import ask , llm_call,pdf_text_read,greet_check_chain
from icecream import ic 
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import asyncio
import datetime


ic.enable()
# ic.disable()


st.set_page_config(page_title="PaperQueryAI", page_icon="🤖", layout="wide")

st.title("PaperQueryAI: Chatbot Based On Research Papers")
st.markdown('Processing time is approximately 40-50 seconds per query.')
conn = st.connection("gsheets", type=GSheetsConnection)

existing_data=conn.read(worksheet="PaperQueryAI",ttl=5)

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display references in an expandable container
        if (
            message["role"] == "assistant"
            and "references" in message
            and message["references"]
        ):
            with st.expander("🔗 View References", expanded=False):
                for paper_name, paper_link in message["references"].items():
                    st.markdown(f"- [{paper_name}]({paper_link})")

# User input
if prompt := st.chat_input("Ask your question based on research papers:"):


    # Append user input to session state and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant response
    with st.chat_message("assistant"):
        with st.spinner("Processing your query..."):
            greet_score = greet_check_chain.invoke({"user_query": prompt})

            if greet_score.binary_score == "yes":
                # print something to know that it is a greeting query
                ic("This is a greeting query")
                response="I'm sorry, I didn't understand your input. Is there anything I can help you with?"
                st.markdown(response)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response,
                    }
                )
            else:
                # print something to know that it is a research query
                ic("This is a research query")

                ref, jina_text,pdf_links  = ask(prompt)
                pdf_text = asyncio.run(pdf_text_read(pdf_links))
                print(pdf_text)


                response = st.write_stream(llm_call(prompt, jina_text, pdf_text))

                # Display references in an expandable container
                if ref:
                    with st.expander("🔗 View References", expanded=False):
                        for paper_name, paper_link in ref.items():
                            st.markdown(f"- [{paper_name}]({paper_link})")

    # Append assistant response to session state
                st.session_state.messages.append(
                    {"role": "assistant", "content": response, "references": ref}
                )

    data = pd.DataFrame([{
        "User Question": prompt,
        "LLM Response": response,
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Placeholder for the response
}])
    updated_data = pd.concat([existing_data, data])
    conn.update(data=updated_data,worksheet="PaperQueryAI")
    


