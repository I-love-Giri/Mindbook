# How Sentence Chunking Works (Step by Step)

Suppose we have the following text:

```text
I love Python.
It is easy to learn.
Machine learning is amazing.
AI is changing the world.
```

After running:

```python
sentences = re.split(r'(?<=[.!?])\s+', text)
```

we get:

```python
sentences = [
    "I love Python.",
    "It is easy to learn.",
    "Machine learning is amazing.",
    "AI is changing the world."
]
```

Assume:

```python
max_words = 8
```

---

# Initial State

```python
chunks = []
current_chunk = []
current_length = 0
```

Think of these as three boxes.

```text
chunks
[]

current_chunk
[]

current_length
0
```

## What do they represent?

### `chunks`

Stores **finished chunks**.

```text
Finished Boxes

[]
```

### `current_chunk`

Stores the chunk that is currently being built.

```text
Current Box

[]
```

### `current_length`

Stores the number of words already inside the current chunk.

```text
Words in current box

0
```

---

# First Iteration

The loop starts:

```python
for sentence in sentences:
```

First sentence:

```python
sentence = "I love Python."
```

Split it into words:

```python
words = sentence.split()
```

Result:

```python
["I", "love", "Python."]
```

Word count:

```python
len(words)
```

Output:

```text
3
```

Now Python checks:

```python
if current_length + len(words) <= max_words
```

Current length:

```text
0
```

Sentence length:

```text
3
```

Calculation:

```text
0 + 3 = 3
```

Is:

```text
3 <= 8
```

✅ Yes.

### Add the sentence

```python
current_chunk.append(sentence)
```

Before:

```text
[]
```

After:

```text
[
    "I love Python."
]
```

Update the word count:

```python
current_length += len(words)
```

Before:

```text
0
```

After:

```text
3
```

Current state:

```text
chunks

[]

current_chunk

[
    "I love Python."
]

current_length

3
```

---

# Second Iteration

Sentence:

```text
"It is easy to learn."
```

Split:

```text
["It", "is", "easy", "to", "learn."]
```

Word count:

```text
5
```

Calculation:

```text
Current = 3

New = 5

3 + 5 = 8
```

Check:

```text
8 <= 8
```

✅ Yes.

Current chunk becomes:

```text
[
    "I love Python.",
    "It is easy to learn."
]
```

Current length:

```text
8
```

State:

```text
chunks

[]

current_chunk

[
    "I love Python.",
    "It is easy to learn."
]

current_length

8
```

---

# Third Iteration

Sentence:

```text
Machine learning is amazing.
```

Split:

```text
Machine
learning
is
amazing
```

Word count:

```text
4
```

Calculation:

```text
Current = 8

Sentence = 4

8 + 4 = 12
```

Check:

```text
12 <= 8
```

❌ No.

Python enters the `else` block.

## Save the current chunk

```python
chunks.append(" ".join(current_chunk))
```

Current chunk:

```text
[
    "I love Python.",
    "It is easy to learn."
]
```

Joining produces:

```text
"I love Python. It is easy to learn."
```

Now:

```text
chunks

[
    "I love Python. It is easy to learn."
]
```

Chunk 1 is complete.

## Start a new chunk

```python
current_chunk = [sentence]
```

Current chunk:

```text
[
    "Machine learning is amazing."
]
```

Reset the length:

```python
current_length = len(words)
```

Current length:

```text
4
```

State:

```text
chunks

[
    "I love Python. It is easy to learn."
]

current_chunk

[
    "Machine learning is amazing."
]

current_length

4
```

---

# Fourth Iteration

Sentence:

```text
AI is changing the world.
```

Word count:

```text
5
```

Calculation:

```text
Current = 4

New = 5

4 + 5 = 9
```

Check:

```text
9 <= 8
```

❌ No.

Save the current chunk.

```text
chunks

[
    "I love Python. It is easy to learn.",
    "Machine learning is amazing."
]
```

Start a new chunk:

```text
current_chunk

[
    "AI is changing the world."
]
```

Current length:

```text
5
```

---

# Loop Ends

All sentences have been processed.

However, the final chunk is still sitting in `current_chunk`:

```text
[
    "AI is changing the world."
]
```

It hasn't been saved yet.

That's why we write:

```python
if current_chunk:
```

Meaning:

> If the current chunk is not empty...

Then:

```python
chunks.append(" ".join(current_chunk))
```

Final result:

```python
[
    "I love Python. It is easy to learn.",
    "Machine learning is amazing.",
    "AI is changing the world."
]
```

Finally:

```python
return chunks
```

---

# Visual Summary

Imagine you're packing books into boxes.

Each box can hold **8 books**.

```text
Sentence 1 = 3 books
Sentence 2 = 5 books
Sentence 3 = 4 books
Sentence 4 = 5 books
```

### Start

```text
Box

0 books
```

↓

Add Sentence 1

```text
3 books
```

↓

Add Sentence 2

```text
8 books
```

↓

Next sentence has 4 books

```text
8 + 4 = 12

Too many!
```

↓

Close Box 1

```text
Sentence 1
Sentence 2
```

↓

Open Box 2

```text
Sentence 3
```

↓

Next sentence

```text
4 + 5 = 9

Too many!
```

↓

Close Box 2

↓

Open Box 3

```text
Sentence 4
```

↓

Loop finishes

↓

Close the final box

---

# Common Mistake

The following code is **incorrect** because `return` is inside the loop:

```python
for sentence in sentences:

    ...

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
```

This causes the function to stop after processing only the **first sentence**.

---

# Correct Version

```python
chunks = []
current_chunk = []
current_length = 0

for sentence in sentences:

    words = sentence.split()

    if current_length + len(words) <= self.max_words:
        current_chunk.append(sentence)
        current_length += len(words)

    else:
        chunks.append(" ".join(current_chunk))
        current_chunk = [sentence]
        current_length = len(words)

# Outside the loop
if current_chunk:
    chunks.append(" ".join(current_chunk))

return chunks
```

This version:

- Processes **every sentence**.
- Saves completed chunks whenever the limit is exceeded.
- Saves the final chunk after the loop ends.
- Returns the complete list of chunks.
