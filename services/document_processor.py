from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
import os

class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    def process_document(self, file_path):
        """
        Process the document using LangChain
        """
        try:
            # Load the document
            loader = TextLoader(file_path)
            documents = loader.load()
            
            # Split the text into chunks
            texts = self.text_splitter.split_documents(documents)
            
            # Here you can add more processing logic using LangChain
            # For example: summarization, analysis, etc.
            
            return {
                'status': 'success',
                'message': 'Document processed successfully',
                'chunks': len(texts)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error processing document: {str(e)}'
            } 