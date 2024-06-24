import os
import csv
import nltk
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader, CSVLoader

# Download NLTK resources if not already downloaded
nltk.download('punkt')
nltk.download('stopwords')

# Set OpenAI API key
from dotenv import load_dotenv
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

def detect_delimiter(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        sample = file.read(1000) 
        FormatofCSV = csv.Sniffer().sniff(sample)
        return FormatofCSV.delimiter

documents = []
def process_file(file_path):
    if file_path.endswith('.pdf'):
        loader = PyPDFLoader(file_path)
        documents.extend(loader.load())
    elif file_path.endswith('.docx') or file_path.endswith('.doc'):
        loader = Docx2txtLoader(file_path)
        documents.extend(loader.load())
    elif file_path.endswith('.txt'):
        loader = TextLoader(file_path, encoding='utf-8')
        documents.extend(loader.load())
    elif file_path.endswith('.csv'):
        delimiter = detect_delimiter(file_path)
        loader = CSVLoader(file_path, csv_args={"delimiter": delimiter})
        documents.extend(loader.load())

def file_chunking(emp_type):

    if emp_type in ['W2-FTE', 'W2-Consultant', 'Corp-2-Corp']:
        root_folder = './documents/us'
    else:
        root_folder = './documents/ph'

    # Walk through the directory tree
    for folder, _, files in os.walk(root_folder):
        for file in files:
            file_path = os.path.join(folder, file)
            process_file(file_path)

    # To split and chunks the loaded documents into smaller tokens
    text_splitter = CharacterTextSplitter(separator="\n", chunk_size=400, chunk_overlap=100)
    print("##################################")
    print(documents)
    print("##################################")
    docs = text_splitter.split_documents(documents)

    return docs

prompt_template = """**I am ALiCIA (Automated Live Chatbot Intelligent Agent) built by Seven Seven Corporate Group.** My knowledge comes solely from the documents you provide. 

**Here's how I work:**

* I strive to answer your questions accurately and concisely based on the provided documents.
* If the answer isn't found in the documents, I'll honestly tell you: "I'm sorry, I don't have information about this topic in my knowledge base."
* I won't provide examples unless you explicitly ask for them.
* I can't answer general knowledge questions (math, science, etc.). 
* I only understand and respond in English.

**Documents:**

{context}

**Human:** {question}

**ALiCIA:**
"""
    
PROMPT = PromptTemplate(
    template=prompt_template, 
    input_variables=["context", "question"])


def model_chain(request, temp_id, verbose=True):
    embeddings = OpenAIEmbeddings()
    emp_type = request.session['empType']
    docs = file_chunking(emp_type)
    print("*********************")
    print(docs)
    print("*********************")
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
    vector = FAISS.from_documents(docs, embeddings)
    retriever = vector.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": .65})
    qa_instances = {}

    def inner_model_chain(temp_id, verbose=True):
        # Check if the instance already exists for the temp_id, if not, create a new one
        if temp_id not in qa_instances:
            qa_instances[temp_id] = ConversationalRetrievalChain.from_llm(
                llm,
                retriever,
                return_source_documents=True,
                memory=ConversationBufferWindowMemory(k=7, memory_key="chat_history", return_messages=True, output_key="answer"),
                combine_docs_chain_kwargs={"prompt": PROMPT},
                verbose=verbose
            )

        return qa_instances[temp_id]

    return inner_model_chain(temp_id, verbose)

def model_response(user_prompt, conversation_history, qa):
    response = qa.invoke({"question": user_prompt, 'chat_history': conversation_history})
    conversation_history.append(({'Human': user_prompt, 'AI': response["answer"]}))
    filenames = list(set(os.path.basename(x.metadata['source']) for x in response['source_documents']))
    print("\033[96m Source docs: ", filenames)
    print("\033[0;39m")
    return response['answer'], filenames
