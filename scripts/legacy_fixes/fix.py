with open('src/dense/embeddings.py', 'r') as f:
    text = f.read()
text = text.replace('try:
                self.tokenizer', 'try:\n                self.tokenizer')
text = text.replace('
            except', '\n            except')
text = text.replace('
                print', '\n                print')
text = text.replace('print("Creating InferenceSession...")
            try:
', 'print("Creating InferenceSession...")\n            try:\n')
with open('src/dense/embeddings.py', 'w') as f:
    f.write(text)
