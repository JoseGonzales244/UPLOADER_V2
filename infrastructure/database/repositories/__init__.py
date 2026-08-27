"""
Módulo de repositorios concretos de Base de Datos.
"""
from infrastructure.database.repositories.teradata_repository import TeradataRepository
from infrastructure.database.repositories.speech_repository import SpeechDbRepository

__all__ = ["TeradataRepository", "SpeechDbRepository"]
