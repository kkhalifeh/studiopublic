import os
from django.core.management.base import BaseCommand
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings


class Command(BaseCommand):
    help = "Runs APScheduler."

    def handle(self, *args, **options):
        module_dir = os.path.dirname(__file__)  # get current directory
        loader = TextLoader(module_dir + '/../../knowledge_base/knowledge.txt', encoding="latin-1")
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50)
        texts = text_splitter.split_documents(documents)

        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vectordb = Chroma.from_documents(
            texts,
            embeddings,
            persist_directory=module_dir + "/../../studio_db"
        )

        vectordb.persist()

        print("✅ Vector DB created!")
