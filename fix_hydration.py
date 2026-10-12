with open("src/api/main.py", "r") as f:
    lines = f.readlines()

new_lines = []
in_reranked = False
skip = False
for i, line in enumerate(lines):
    if "def reranked_search(" in line:
        in_reranked = True
        
    if in_reranked and "seen_hashes = set()" in line:
        new_lines.append(line)
        # Add batch query
        batch_code = """        # BATCH FETCH
        doc_ids_to_fetch = [doc_id for doc_id, score in raw_results[:candidate_pool_size + 100]]
        if doc_ids_to_fetch:
            db_docs = session.query(DBDocument).filter(
                DBDocument.int_id.in_(doc_ids_to_fetch), 
                DBDocument.is_deleted == False
            ).all()
            db_doc_map = {d.int_id: d for d in db_docs}
        else:
            db_doc_map = {}

        for doc_id, score in raw_results:
            if len(candidates) >= candidate_pool_size:
                break
                
            db_doc = db_doc_map.get(doc_id)
            if db_doc is None:
                continue
                
            if db_doc.content_hash in seen_hashes:
                continue
            seen_hashes.add(db_doc.content_hash)
"""
        new_lines.append(batch_code)
        
        # Now we skip lines until `url = db_doc.url`
        skip = True
        continue
        
    if skip:
        if "url = db_doc.url" in line:
            skip = False
            new_lines.append(line)
        continue
        
    new_lines.append(line)

with open("src/api/main.py", "w") as f:
    f.writelines(new_lines)

print("Fixed src/api/main.py")
