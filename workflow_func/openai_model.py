from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI


# Call custom retriever
from .langchain_custom_retriever import RetrieverWithScores

from datetime import date

#adding source docs to chatlog transcript
from gpt4all_app.models import Chatlog

#fetch s3 files
from .s3_files import *

from dotenv import load_dotenv
load_dotenv()


openai_param = db_connect("s3_bucket.openai_param")
prompt = openai_param["prompt"]
similarity_score_threshold = openai_param["similarity_score_threshold"]
llm_model = openai_param["llm_model"]
llm_temperature = openai_param["llm_temperature"] 

print('llm_model', llm_model)
print('temp', llm_temperature)

qa_instances = {}
store = {}

llm = ChatOpenAI(model=llm_model, temperature=llm_temperature)



def model_chain(request, temp_id):
    
    try:
        user_information = request.session['user_info']
    except KeyError:
        user_information = ""
        

    contextualize_q_system_prompt = """Given a chat history and the latest user question \
    which might reference context in the chat history, formulate a standalone question \
    which can be understood without the chat history. Do NOT answer the question, \
    just reformulate it if needed and otherwise return it as is."""
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            
        ]
    )

    current_date = date.today().strftime("%B %d, %Y")

    qa_system_prompt =  prompt.format(user_information, current_date)

    qa_system_prompt += """
    This is your knowledge base: \"""{context}\"""
    
    """


    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )


    # Check if the instance already exists for the temp_id, if not, create a new one
    if temp_id not in qa_instances:
        pass
    if len([])==0:

        vector = final_vector(request)
        retriever = RetrieverWithScores.from_vector_store(vector_store=vector, search_type="similarity_score_threshold", search_kwargs={"score_threshold": similarity_score_threshold})


        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, contextualize_q_prompt
            )

        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)


        def get_session_history(session_id: str) -> BaseChatMessageHistory:
            if session_id not in store:
                store[session_id] = ChatMessageHistory()
            return store[session_id]
        
        
        qa_instances[temp_id] = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
            verbose =  True
        )

    return qa_instances[temp_id]


def model_response(request, user_prompt, conversation_history, qa):  

        session_id = request.session['id']
        response = qa.invoke(
                    {"input": user_prompt},
                    config={"configurable": {"session_id": session_id}},
                )
        conversation_history.append(({'Human': user_prompt, 'ALiCIA': response["answer"]}))
        filenames = list(set(os.path.basename(x.metadata['source']) for x in response['context']))
        print(colors.CYAN + "Source docs: ", str(filenames) + colors.END)

        print(response['answer'])


        context = response['context'] 
        chat_history = response['chat_history']
        # the docs are already sorted by similarity score from the custom retriever -- greatest to least
        content_dict = {doc.page_content: doc.metadata['source'] for doc in context}
        content_dict_scores = [doc.metadata['similarity_score'] for doc in context]
        
        #adding content data to chatlog transcript
        log = Chatlog.objects.get(id=session_id)
        log.transcript += "\n\nKnowledge base provided:"
        
        print(colors.YELLOW + '\n\nKnowledge base provided:' + colors.END)

        # print(content_dict)

        for index, (key, value) in enumerate(content_dict.items()):
            print(colors.YELLOW + '\n\n' + '#'+str(index+1) + ' Source: ' + str(value) +'\n' + colors.END)
            print(colors.YELLOW + str(key) + colors.END)
            print(colors.YELLOW + "\nSimilarity Score: ", str(round(content_dict_scores[index], 4)) + " / ", str(similarity_score_threshold) + "00" + colors.END)    
        log.save()

        print(colors.GREEN + '\n\nChat History: \n\n' + str(chat_history) + '\n\n' + colors.END)
        # print(colors.CYAN + "Similariy Score: ", round())

        return response['answer']




