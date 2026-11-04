# Write with Lean and Typst

This tool exists because I refuse to learn verso. I already learnt markdown, latex, and typst. I wanted to make lean code slides a la verso, without actually writing verso. If you want to see the results, check out the HTML and PDF files in [Samples](#samples). I first put this together for lecture slides. Then I absolutely used AI to clean up the mess and create a template. This repo is AI-pilled. Use at your own discretion. I am of course happy to accept bug reports and pull requests.

## Contents

- [Samples](#samples)
- [First-time setup](#first-time-setup)
- [Second time onwards](#second-time-onwards)
- [Where to begin writing](#where-to-begin-writing)
- [Update the documents as you write](#update-the-documents-as-you-write)
- [How the code works](ImplementationNotes.md)
- [AI disclosure](#ai-disclosure)

## Samples

Visit the [sample website](https://shreyas4991.github.io/TypstVerso/) or open a
document below. The HTML examples run directly in your browser with interactive
Lean tooltips; the PDFs are available for reading or printing. No installation
is needed to view these compiled examples.

PDF tooltip rendering depends heavily on the PDF reader. The HTML version is
likely to render tooltips more reliably.

| Template | HTML | PDF |
| --- | --- | --- |
| Article | [HTML](https://shreyas4991.github.io/TypstVerso/documents/article/build/main.html) | [PDF](https://shreyas4991.github.io/TypstVerso/documents/article/build/main.pdf) |
| Book | [HTML](https://shreyas4991.github.io/TypstVerso/documents/book/build/main.html) | [PDF](https://shreyas4991.github.io/TypstVerso/documents/book/build/main.pdf) |
| Slides | [HTML](https://shreyas4991.github.io/TypstVerso/documents/slides/build/main.html) | [PDF](https://shreyas4991.github.io/TypstVerso/documents/slides/build/main.pdf) |

The website updates automatically when changes to these compiled samples or
`index.html` are pushed to `main`. After editing a template, run
`.venv/bin/python build.py --all` and commit its updated HTML and PDF files to
refresh the published examples.

## First Time Setup

### 1. Check the required installations

Install these tools on your computer:

- [Lean](https://lean-lang.org/install/), including elan and Lake.
- [Typst](https://typst.app/open-source/) 0.15 or later.
- [Python](https://www.python.org/downloads/) 3.9 or later.
- [Git](https://git-scm.com/downloads/).

Check that these commands work in your terminal:

```sh
lean --version
lake --version
typst --version
python3 --version
git --version
```

On Windows, use `py --version` for Python. If a command is missing, complete
that tool's installation before continuing.

### 2. Create a repository from the template

On [GitHub](https://github.com/Shreyas4991/TypstVerso), select **Use this template →
Create a new repository**. Choose an owner and name, then create the repository.

Clone your new repository and enter its folder. Replace `YOUR-USER` and
`YOUR-REPO` below:

```sh
git clone https://github.com/YOUR-USER/YOUR-REPO.git
cd YOUR-REPO
```

### 3. Install the Python dependency and build

Run these commands from the repository folder, which contains `build.py`.

On macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python build.py --all
```

On Windows:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe build.py --all
```

In the remaining commands, Windows users should replace `.venv/bin/python` with
`.venv\Scripts\python.exe`.

The first build downloads Lean dependencies, so it needs an internet connection
and may take a while. Wait until the command finishes.

Each sample has its own `build/` folder. Open `main.html` there to read it in your
browser, or `main.pdf` to read or print it.

## Second time onwards

You only need to do the setup once. When you come back to the project:

1. Open the template folder in your editor.
2. Open a terminal in that folder. It should contain `build.py`.
3. Run this command:

```sh
.venv/bin/python build.py --watch --all
```

On Windows, use:

```powershell
.venv\Scripts\python.exe build.py --watch --all
```

This makes all three documents, then updates them when you save changes.
Leave the terminal open while you write. Refresh your browser to see the changes.
Press `Ctrl+C` in the terminal when you want to stop.

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
.venv/bin/python build.py --watch --all
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
