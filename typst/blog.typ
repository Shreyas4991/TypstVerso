// Copyright 2026 Shreyas Srinivas
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Dates are set by the author, never inferred from file modification times.
#let blog-date(year, month, day) = datetime(year: year, month: month, day: day)

// A post is data until blog renders the sorted collection.
#let blog-post(title: none, date: none, body) = {
  assert(title != none, message: "Each blog post needs a title.")
  assert(type(date) == datetime, message: "Set each post's date with blog-date(year, month, day).")
  assert(date.year() != none and date.month() != none and date.day() != none,
    message: "Each blog post needs a complete calendar date.")
  (title: title, date: date, body: body)
}

#let blog(title: [Mathematical notes], author: "Your Name", posts) = {
  set document(title: title, author: author)
  set page(paper: "iso-b5", margin: (x: 18mm, y: 20mm), numbering: none)
  set text(size: 10pt)
  set par(justify: true)
  set heading(numbering: none)
  show heading.where(level: 1): it => {
    pagebreak(weak: true)
    it
  }

  text(size: 27pt, weight: "bold", title)
  parbreak()
  author
  parbreak()
  v(1cm)
  text(size: 16pt, weight: "bold")[Posts]
  parbreak()
  // Linked titles only: no chapter numbers, dot leaders, or page references.
  context {
    for post in query(heading.where(level: 1)).filter(h => h.outlined) {
      block(link(post.location(), post.body))
    }
  }

  // A negative calendar key gives latest-first order and keeps equal-date posts
  // in their source order because Typst's sort is stable.
  let ordered = posts.sorted(key: post => -(
    post.date.year() * 10000 + post.date.month() * 100 + post.date.day()))
  for post in ordered {
    heading(level: 1, post.title)
    block(text(fill: rgb("626a64"), post.date.display("[day] [month repr:long] [year]")))
    post.body
  }
}
