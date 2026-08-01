"""Six evals over one ClauseAnswer. All deterministic — no judge anywhere.

That is the point of moving to CUAD. The previous domain (forecasting a stock's
next move) had no decidable ground truth, so correctness had to be inferred from
outcomes that were mostly noise, and an LLM judge had to fill the gap and
returned 1.00 on all 20 cases. Here a lawyer already located the answer, so
every metric below is arithmetic over a labelled span.

The metrics split along the line that matters for RAG:

  retrieval    context_recall  — did the retrieved chunks contain the gold span?
  generation   token_f1        — did the answer overlap the gold span?
               exact_match     — stricter, same comparison
               citation_fidelity — is the answer actually IN the excerpts, or is
                                 the model answering from memory?
  the hard half
               abstention      — on the 146 cases where lawyers marked the
                                 clause ABSENT, did it say so? Top-k always
                                 returns k plausible-looking chunks, so this is
                                 where a RAG system invents a clause.

`spread` on the scorecard keeps all of it honest: a metric that never varies
across the case set carries no information whatever its mean.
"""

import re
import statistics
from dataclasses import dataclass

# Legal text is full of section numbers, parentheses and quoted defined terms;
# comparing raw strings makes trivially-equivalent answers look different. This
# is the standard SQuAD normalisation (lowercase, drop punctuation and articles,
# collapse whitespace) so that token overlap measures content, not typography.
_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = re.compile(r"[^\w\s]")


def normalize(text: str) -> str:
    return " ".join(_ARTICLES.sub(" ", _PUNCT.sub(" ", text.lower())).split())


def tokens(text: str) -> list[str]:
    return normalize(text).split()


@dataclass
class Score:
    name: str
    value: float  # 0-1, higher is better, for every metric
    detail: str


def token_f1(pred: str, golds: list[str]) -> float:
    """SQuAD token-F1 against the best-matching gold span.

    F1 rather than containment, because both failure directions are real: an
    answer that returns the entire contract would score perfect recall while
    being useless, and a two-word answer would score perfect precision while
    missing the clause. CUAD often lists several acceptable spans, so this takes
    the best — matching any one of them is correct.
    """
    if not golds:
        return 0.0
    p = tokens(pred)
    best = 0.0
    for gold in golds:
        g = tokens(gold)
        if not p or not g:
            continue
        common = 0
        pool = list(g)
        for t in p:
            if t in pool:
                pool.remove(t)
                common += 1
        if common:
            prec, rec = common / len(p), common / len(g)
            best = max(best, 2 * prec * rec / (prec + rec))
    return best


def exact_match(pred: str, golds: list[str]) -> float:
    """Normalised containment either way — the model quoting a slightly wider or
    narrower window than the annotator is not a different answer. Stricter than
    token_f1 (order and adjacency must hold), reported alongside it rather than
    instead of it."""
    p = normalize(pred)
    if not p:
        return 0.0
    return float(any(p in normalize(g) or normalize(g) in p for g in golds if g))


def context_recall(chunks: list, spans: list[tuple[int, int]]) -> Score:
    """Did retrieval actually surface the text the lawyer highlighted?

    Pure retrieval quality, independent of what the model then does with it —
    which is the split that tells you which half to fix. Uses character offsets
    rather than string search: the gold span is defined by position in the
    contract, and the same sentence can appear twice.
    """
    if not spans:
        return Score("context_recall", 1.0, "no gold span (absent clause)")
    hit = 0
    for gs, ge in spans:
        for c in chunks:
            if c.start < ge and gs < c.start + len(c.text):
                hit += 1
                break
    ratio = hit / len(spans)
    return Score("context_recall", ratio, f"{hit}/{len(spans)} gold spans retrieved")


def citation_fidelity(pred: str, chunks: list) -> Score:
    """Is the answer actually in the excerpts it was given?

    Catches the model answering from parametric memory or paraphrasing the
    contract into something that was never written. Compares normalised text so
    that whitespace and section numbering do not cause false alarms, and uses a
    token-overlap floor rather than exact containment because the model routinely
    stitches two adjacent excerpt lines together.
    """
    if not pred.strip():
        return Score("citation_fidelity", 1.0, "no answer to attribute")
    if not chunks:
        return Score("citation_fidelity", 0.0, "answered with no context at all")
    haystack = normalize(" ".join(c.text for c in chunks))
    if normalize(pred) in haystack:
        return Score("citation_fidelity", 1.0, "verbatim in excerpts")
    pool, common = haystack.split(), 0
    seen = set(pool)
    pt = tokens(pred)
    for t in pt:
        if t in seen:
            common += 1
    ratio = common / len(pt) if pt else 0.0
    return Score(
        "citation_fidelity", ratio,
        f"{ratio:.0%} of answer tokens appear in excerpts",
    )


def abstention(found: bool, impossible: bool) -> Score:
    """The hard half, and the one CUAD makes measurable.

    Top-k retrieval cannot return nothing. Ask about a cap on liability in a
    contract that has none and the retriever still hands over six chunks of
    indemnity and warranty-disclaimer language that look exactly like the real
    thing. Whether the model then invents a clause is the single most useful
    thing to know about a contract-review RAG system, and CUAD's `is_impossible`
    flag is a lawyer's answer to it.
    """
    if impossible:
        return Score(
            "abstention", float(not found),
            "correctly absent" if not found else "INVENTED a clause that is not there",
        )
    return Score(
        "abstention", float(found),
        "found it" if found else "missed a clause that IS there",
    )


def score_all(ans, case, chunks: list) -> list[Score]:
    """All six, in the order retrieval → generation → the hard half.

    token_f1 and exact_match only apply where there is something to match, so on
    an absent-clause case they are omitted rather than scored 0 — a model that
    correctly says "not present" has not got the extraction wrong, it has been
    graded by `abstention` instead. Scoring it 0 here would drag the mean down
    for the one behaviour the day most wants to reward.
    """
    scores = [context_recall(chunks, case.gold_spans)]
    if not case.impossible:
        scores += [
            Score("token_f1", token_f1(ans.answer, case.gold_answers), f"vs {len(case.gold_answers)} gold span(s)"),
            Score("exact_match", exact_match(ans.answer, case.gold_answers), ""),
        ]
    scores.append(citation_fidelity(ans.answer, chunks))
    scores.append(abstention(ans.found, case.impossible))
    return scores


def _demo() -> None:
    """ponytail: one assert-based self-check. The metric is the deliverable, and
    on the previous build three of four bugs found were in the metric rather
    than the model — every assert here pins a case that could silently invert a
    finding."""
    assert normalize("The (a) Cap, on Liability!") == "cap on liability"
    assert token_f1("cap on liability", ["cap on liability"]) == 1.0
    assert token_f1("", ["anything"]) == 0.0
    assert token_f1("cap", []) == 0.0  # absent clause: nothing to match
    # Partial overlap must land strictly between 0 and 1, or F1 is behaving
    # like containment and the metric is not measuring precision at all.
    assert 0 < token_f1("a cap on liability applies", ["cap on liability"]) < 1
    # Best-of-several golds, since CUAD lists multiple acceptable spans.
    assert token_f1("audit rights", ["cap on liability", "audit rights"]) == 1.0

    assert exact_match("Cap on Liability", ["the cap on liability clause"]) == 1.0
    assert exact_match("", ["x"]) == 0.0
    assert exact_match("indemnification", ["cap on liability"]) == 0.0

    class C:
        def __init__(self, start, text):
            self.start, self.text, self.chunk_id = start, text, "c"

    # Overlap, not containment: a gold span straddling a chunk boundary is
    # retrieved. Off-by-one here would silently deflate retrieval quality.
    assert context_recall([C(0, "x" * 100)], [(50, 150)]).value == 1.0
    assert context_recall([C(0, "x" * 100)], [(100, 150)]).value == 0.0
    assert context_recall([C(0, "x")], []).value == 1.0  # absent clause

    assert citation_fidelity("cap on liability", [C(0, "The cap on liability is $1m")]).value == 1.0
    assert citation_fidelity("", [C(0, "anything")]).value == 1.0
    assert citation_fidelity("totally unrelated wording", []).value == 0.0

    assert abstention(found=False, impossible=True).value == 1.0
    assert abstention(found=True, impossible=True).value == 0.0
    assert abstention(found=True, impossible=False).value == 1.0
    assert abstention(found=False, impossible=False).value == 0.0
    print("evals self-check ok")


if __name__ == "__main__":
    _demo()
