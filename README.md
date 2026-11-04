# Write with Lean and Typst

This tool exists because I refuse to learn verso. I already learnt markdown, latex, and typst. I wanted to make lean code slides a la verso, without actually writing verso. If you want to see the results, go to the `documents` folder, open one of the three variants of documents I have set up as a template (article/book/slides), open the `build` subfolder, and check out the html and pdf in your own browser/pdf-reader. I first put this together for lecture slides. Then I absolutely used AI to clean up the mess and create a template. This repo is absolutely AI-pilled. Use at your own discretion. 

## Set up the template

### 1. Install the tools

Install these tools on your computer:

- [Lean](https://lean-lang.org/install/) checks your proofs. Follow its setup guide.
- [Typst](https://typst.app/open-source/) makes the finished pages. Use version 0.15 or later.
- [Python](https://www.python.org/downloads/) runs the included `build.py` program. Use version 3.9 or later.
- [Git](https://git-scm.com/downloads/) downloads the Lean files this template needs.

### 2. Open this folder

Open this folder in the app you use to edit text files. I used vscode. I have the lean extension and tinymist already installed. You should be able to see a file called  `build.py` 


### 3. Prepare Python

Run these two commands once to install the Python files this project needs.

On macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

On Windows:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

In the remaining commands, Windows users should replace `.venv/bin/python` with
`.venv\Scripts\python.exe`.

### 4. Make all the sample documents

Here, **build** means turn your writing into finished files. To build all three
samples, run:

```sh
.venv/bin/python build.py --all
```

The first run downloads files, so it needs an internet connection and may take
a while. Wait until the command finishes.

Each sample has its own `build/` folder. Open `main.html` there to read it in your
browser, or `main.pdf` to read or print it.

## Where to begin writing

Choose the file for the kind of document you want to write:

| I want to write | Start with | Finished files go in |
| --- | --- | --- |
| Slides | [documents/slides/main.typ](documents/slides/main.typ) | `documents/slides/build/` |
| An article | [documents/article/main.typ](documents/article/main.typ) | `documents/article/build/` |
| A book | [documents/book/main.typ](documents/book/main.typ) | `documents/book/build/` |

Replace the sample text with your own writing. Keep the first `#import` lines;
they let your document use Lean examples and its page style.

Write your Lean definitions and proofs in
[LeanProject/LeanProject/Basic.lean](LeanProject/LeanProject/Basic.lean).
The sample proofs sit between `namespace Demo` and `end Demo`.
Keep `@[expose] public section` above them; it makes your definitions available
to your documents.
A proof named `identity_pair` in that section is called `Demo.identity_pair`
when you use it in your document.

For example, add this line to your `.typ` file to show that proof:

```typst
#lean-quote("Demo.identity_pair")
```

To build just one document, use the matching command:

```sh
# Slides
.venv/bin/python build.py --document documents/slides

# Article
.venv/bin/python build.py --document documents/article

# Book
.venv/bin/python build.py --document documents/book
```

## Update the documents as you write

To **watch** means to leave the program running so it notices saved changes and
builds the documents again. To watch all three documents, run:

```sh
.venv/bin/python build.py --all --watch
```

Or watch just the article:

```sh
.venv/bin/python build.py --document documents/article --watch
```

Replace `article` with `slides` or `book` to watch either of those instead.

Leave the terminal open. Save a `.typ` file to update the finished documents.
Refresh your browser to see the result. Press `Ctrl+C` in the terminal to stop.

For more options and an explanation of how the code works, see
[ImplementationNotes.md](ImplementationNotes.md).

### AI Disclosure 

Yes! Ergo, use at your own risk. 
