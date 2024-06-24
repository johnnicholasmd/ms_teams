# for custom retriever for retrieving similarity score
from langchain_core.vectorstores import VectorStoreRetriever, VectorStore
from langchain_core.retrievers import BaseRetriever
from langchain_core.pydantic_v1 import Field
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    ClassVar,
    Collection,
)

from langchain_core.callbacks.manager import (
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document

# Custom Retriever for retrieving source docs metadata and similarity score
class RetrieverWithScores(BaseRetriever):
    """
    A retriever that returns documents with their similarity scores.

    OLD:
        retriever = my_vector_store.as_retriever(search_type="similarity")

    NEW:
        retriever = RetrieverWithScores.from_vector_store(my_vector_store, search_type="similarity")
    """

    vectorstore: VectorStore
    """VectorStore to use for retrieval."""
    search_type: str = "similarity"
    """Type of search to perform. Defaults to "similarity"."""
    search_kwargs: dict = Field(default_factory=dict)
    """Keyword arguments to pass to the search function."""
    allowed_search_types: ClassVar[Collection[str]] = (
        "similarity",
        "similarity_score_threshold",
        "mmr",
    )


    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        if self.search_type == "similarity":
            docs_and_similarities = self.vectorstore._similarity_search_with_relevance_scores(query, **self.search_kwargs)
        elif self.search_type == "similarity_score_threshold":
            docs_and_similarities = (
                self.vectorstore.similarity_search_with_relevance_scores(
                    query, **self.search_kwargs
                )
            )
        elif self.search_type == "mmr":
            docs = self.vectorstore.max_marginal_relevance_search(
                query, **self.search_kwargs
            )
            docs_and_similarities = [(doc, 0.0) for doc in docs]
        else:
            raise ValueError(f"search_type of {self.search_type} not allowed.")

        for doc, score in docs_and_similarities:
            doc.metadata = {**doc.metadata, **{"similarity_score": score}}
        return [doc for (doc, _) in docs_and_similarities]

    @staticmethod
    def from_vector_store(vector_store: VectorStore, 
                        #   search_kwargs: dict = Field(default_factory=dict),  
                          **kwargs: Any) -> "RetrieverWithScores":
        """
        Return VectorStoreRetriever initialized from this VectorStore.
        This is basically a copy of VectorStore.as_retriever method.

        """
        tags = kwargs.pop("tags", None) or []
        tags.extend(vector_store._get_retriever_tags())
        return RetrieverWithScores(vectorstore=vector_store, **kwargs, tags=tags)

