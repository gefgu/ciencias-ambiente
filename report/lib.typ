// Template: relatório técnico — Ciências do Ambiente / UTFPR
// Paleta idêntica à do painel Streamlit (src/m1/theme.py)
#let teal = rgb("#0F766E")
#let ink = rgb("#1F2933")
#let muted = rgb("#6B7280")
#let rule = rgb("#E5E3DA")
#let amber = rgb("#D97706")
#let red = rgb("#B91C1C")

#let sans = ("Noto Sans", "DejaVu Sans")
#let mono = ("DejaVu Sans Mono", "Noto Sans Mono")

/// Selo inline para dados provisórios (substituir após medição em campo).
#let ph(body: [placeholder]) = box(
  fill: rgb("#FEF3C7"), stroke: 0.5pt + rgb("#FCD34D"), radius: 8pt, inset: (x: 5pt, y: 1.5pt), baseline: 1.5pt,
  text(size: 7.5pt, weight: "bold", fill: rgb("#92400E"), upper(body)),
)

/// Caixa de destaque lateral.
#let callout(title: none, color: teal, body) = block(
  width: 100%, inset: (x: 11pt, y: 9pt), radius: 3pt, fill: color.lighten(92%), stroke: (left: 3pt + color), breakable: false,
)[
  #if title != none { text(weight: "bold", fill: color.darken(15%), size: 9.5pt)[#title]; parbreak() }
  #set text(size: 9.5pt)
  #body
]
#let aviso(body) = callout(title: "Dado provisório", color: amber, body)

/// Linha de metadados da capa.
#let meta(k, v) = (text(size: 8pt, fill: muted, weight: "bold", upper(k)), text(size: 10pt, v))

#let report(
  title: "", subtitle: "", course: "", program: "", milestone: "", authors: (), date: "", abstract: none, body,
) = {
  set document(title: title, author: authors.map(a => a.name))
  set page(
    paper: "a4", margin: (x: 2.3cm, top: 2.6cm, bottom: 2.4cm),
    header: context {
      if counter(page).get().first() > 1 {
        set text(size: 8pt, fill: muted)
        grid(columns: (1fr, auto), [#milestone · #course], [UTFPR])
        v(-5pt); line(length: 100%, stroke: 0.5pt + rule)
      }
    },
    footer: context {
      set text(size: 8pt, fill: muted)
      line(length: 100%, stroke: 0.5pt + rule); v(-4pt)
      grid(columns: (1fr, auto), title, [#counter(page).display() / #counter(page).final().first()])
    },
  )
  set text(font: sans, size: 10pt, fill: ink, lang: "pt", region: "br")
  set par(justify: true, leading: 0.68em, spacing: 1.05em)
  set heading(numbering: "1.1")
  show heading: it => {
    set text(font: sans, fill: if it.level == 1 { teal } else { ink }, weight: if it.level == 1 { "bold" } else { "semibold" })
    let sz = (16pt, 12pt, 10.5pt).at(calc.min(it.level, 3) - 1)
    set text(size: sz)
    v(if it.level == 1 { 1.3em } else { 0.9em }, weak: true)
    block(sticky: true)[
      #if it.numbering != none { counter(heading).display(it.numbering); h(0.6em) }#it.body
      #if it.level == 1 { v(-0.55em); line(length: 100%, stroke: 0.8pt + teal.lighten(55%)) }
    ]
    v(0.45em, weak: true)
  }
  show raw: set text(font: mono, size: 8.5pt)
  show raw.where(block: true): it => block(width: 100%, fill: rgb("#F5F5F0"), stroke: 0.5pt + rule, radius: 3pt, inset: 8pt, it)
  show link: set text(fill: teal)
  show figure.caption: it => {
    set text(size: 8.5pt, fill: muted)
    context [#text(weight: "bold", fill: ink)[#it.supplement #it.counter.display(it.numbering).] #it.body]
  }
  set figure(gap: 0.9em)
  show figure.where(kind: table): set figure.caption(position: top)
  show figure.where(kind: table): set block(breakable: true)
  show table: set text(size: 8.5pt)
  show table: set par(justify: false)
  set table(
    stroke: (x, y) => (bottom: if y == 0 { 0.8pt + teal } else { 0.4pt + rule }),
    inset: (x: 6pt, y: 5pt), fill: (x, y) => if y == 0 { teal.lighten(90%) },
  )
  show table.cell.where(y: 0): set text(weight: "bold", size: 8pt)
  set list(indent: 0.4em, body-indent: 0.5em, marker: text(fill: teal)[•])
  set enum(indent: 0.4em, body-indent: 0.5em)
  show outline.entry.where(level: 1): it => { v(0.3em); strong(it) }

  // ---- capa (bloco no topo da 1ª página) ----
  block(width: 100%, fill: teal, inset: (x: 22pt, y: 22pt), radius: 4pt)[
    #set text(fill: white)
    #text(size: 8.5pt, weight: "bold", tracking: 0.12em)[#upper(milestone) · #upper(program)]
    #v(6pt)
    #par(justify: false)[#text(size: 23pt, weight: "bold", hyphenate: false)[#title]]
    #v(2pt)
    #par(justify: false)[#text(size: 12pt, fill: white.darken(8%), hyphenate: false)[#subtitle]]
  ]
  v(10pt)
  grid(columns: (auto, 1fr), column-gutter: 14pt, row-gutter: 7pt,
    ..meta("Unidade curricular", course), ..meta("Local de estudo", "Quadrilátero Central de Curitiba"),
    ..meta("Equipe", authors.map(a => [#a.name #text(fill: muted, size: 8.5pt)[(#a.role)]]).join([ · ])), ..meta("Data", date))
  v(8pt)
  line(length: 100%, stroke: 0.5pt + rule)
  if abstract != none {
    v(4pt)
    block(inset: (x: 0pt))[#text(weight: "bold", size: 9pt, fill: teal)[RESUMO]#v(-4pt)#abstract]
  }
  v(6pt)
  outline(title: text(size: 11pt, fill: teal)[Sumário], indent: 1.2em, depth: 2)
  pagebreak()
  body
}
