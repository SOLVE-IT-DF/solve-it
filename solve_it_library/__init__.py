"""
SOLVE-IT Knowledge Base Library (`solve_it_library`)

This package provides programmatic access to the SOLVE-IT knowledge base data.

The KnowledgeBase class now automatically loads SOLVE-IT-X extensions from the
extension_data directory. Extensions can be disabled by passing enable_extensions=False
to the KnowledgeBase constructor.

"""

from .solveit_library import KnowledgeBase, SOLVEITDataError

__all__ = ["KnowledgeBase", "SOLVEITDataError"]
