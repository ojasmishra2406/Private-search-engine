from typing import Dict, List, Set
from dataclasses import dataclass

@dataclass
class Posting:
    doc_id: int
    term_freq: int
    positions: List[int]

class InvertedIndex:
    def __init__(self):
        # Term Dictionary: term (str) -> term_id (int)
        self.term_to_id: Dict[str, int] = {}
        self.id_to_term: Dict[int, str] = {}
        self.next_term_id: int = 0
        
        # Document ID mapping: external_id (str) -> doc_id (int)
        self.ext_to_int_doc_id: Dict[str, int] = {}
        self.int_to_ext_doc_id: Dict[int, str] = {}
        self.next_doc_id: int = 0
        
        # Inverted Index: term_id -> List[Posting]
        self.postings: Dict[int, List[Posting]] = {}
        
        # Forward Index: doc_id -> List[term_id] (used for index maintenance/deletions)
        self.forward_index: Dict[int, List[int]] = {}
        
        # Document Statistics: doc_id -> doc_length (tokens)
        self.doc_lengths: Dict[int, int] = {}
        self.total_docs: int = 0
        self.total_tokens: int = 0

    def _get_or_create_term_id(self, term: str) -> int:
        if term not in self.term_to_id:
            tid = self.next_term_id
            self.term_to_id[term] = tid
            self.id_to_term[tid] = term
            self.postings[tid] = []
            self.next_term_id += 1
            return tid
        return self.term_to_id[term]

    def _get_or_create_doc_id(self, ext_id: str) -> int:
        if ext_id not in self.ext_to_int_doc_id:
            did = self.next_doc_id
            self.ext_to_int_doc_id[ext_id] = did
            self.int_to_ext_doc_id[did] = ext_id
            self.next_doc_id += 1
            return did
        return self.ext_to_int_doc_id[ext_id]

    def add_document(self, ext_id: str, tokens: List[str]):
        """Adds a document to the index. Updates it if it already exists."""
        # If document exists, delete it first to ensure clean state
        if ext_id in self.ext_to_int_doc_id:
            did = self.ext_to_int_doc_id[ext_id]
            if did in self.forward_index:
                self.delete_document(ext_id)
                
        doc_id = self._get_or_create_doc_id(ext_id)
        
        term_positions: Dict[int, List[int]] = {}
        term_ids: List[int] = []
        
        for pos, token in enumerate(tokens):
            tid = self._get_or_create_term_id(token)
            term_ids.append(tid)
            if tid not in term_positions:
                term_positions[tid] = []
            term_positions[tid].append(pos)
            
        # Update Forward Index
        self.forward_index[doc_id] = term_ids
        
        # Update Postings
        for tid, positions in term_positions.items():
            self.postings[tid].append(Posting(
                doc_id=doc_id,
                term_freq=len(positions),
                positions=positions
            ))
            
        # Update Document Statistics
        doc_length = len(tokens)
        self.doc_lengths[doc_id] = doc_length
        self.total_docs += 1
        self.total_tokens += doc_length

    def delete_document(self, ext_id: str):
        """Removes a document from the index using the forward index."""
        if ext_id not in self.ext_to_int_doc_id:
            return
            
        doc_id = self.ext_to_int_doc_id[ext_id]
        if doc_id not in self.forward_index:
            return
            
        term_ids = self.forward_index[doc_id]
        unique_term_ids = set(term_ids)
        
        # Remove from inverted index
        for tid in unique_term_ids:
            self.postings[tid] = [p for p in self.postings[tid] if p.doc_id != doc_id]
            
        # Update statistics
        doc_length = self.doc_lengths[doc_id]
        self.total_docs -= 1
        self.total_tokens -= doc_length
        
        # Remove from forward index and lengths
        del self.forward_index[doc_id]
        del self.doc_lengths[doc_id]
        
    def get_average_document_length(self) -> float:
        if self.total_docs == 0:
            return 0.0
        return self.total_tokens / self.total_docs
