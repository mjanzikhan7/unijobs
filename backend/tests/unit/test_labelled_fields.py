"""Reading the labelled fields off a vacancy detail page.

Written before the code, per the working agreement for ``crawler/``.

Nearly every university portal states the same handful of facts as label/value pairs - Location,
Salary, Hours, Contract Type, Placed On, Closes, Job Ref - and the detail fallback previously
kept only the title and the description, discarding all of them. The markup differs (definition
list, table, paired divs); the shape does not.
"""

from __future__ import annotations

from datetime import date

import pytest

from crawler.extraction import apply_labelled_fields, labelled_fields
from crawler.types import RawVacancy

TABLE_HTML = """
<table>
  <tr><th>Location:</th><td>Cambridge</td>
      <th>Placed On:</th><td>7th August 2026</td></tr>
  <tr><th>Salary:</th><td>&pound;35,608 to &pound;46,049 per annum</td>
      <th>Closes:</th><td>6th September 2026</td></tr>
  <tr><th>Hours:</th><td>Full Time</td>
      <th>Job Ref:</th><td>NM50033</td></tr>
  <tr><th>Contract Type:</th><td>Fixed-Term/Contract</td></tr>
</table>
"""

DL_HTML = """
<dl>
  <dt>Location</dt><dd>Cambridge</dd>
  <dt>Salary</dt><dd>&pound;35,608 to &pound;46,049 per annum</dd>
  <dt>Contract Type</dt><dd>Fixed-Term/Contract</dd>
  <dt>Closes</dt><dd>6th September 2026</dd>
</dl>
"""


def test_a_table_of_label_value_pairs_is_read() -> None:
    fields = labelled_fields(TABLE_HTML)

    assert fields["location"] == "Cambridge"
    assert fields["hours"] == "Full Time"
    assert fields["contract type"] == "Fixed-Term/Contract"


def test_several_pairs_on_one_row_are_all_read() -> None:
    """Real markup puts two label/value pairs side by side to save vertical space."""
    fields = labelled_fields(TABLE_HTML)

    assert fields["placed on"] == "7th August 2026"
    assert fields["job ref"] == "NM50033"


def test_a_definition_list_is_read() -> None:
    fields = labelled_fields(DL_HTML)

    assert fields["location"] == "Cambridge"
    assert fields["closes"] == "6th September 2026"


def test_paired_divs_are_read() -> None:
    html = """
    <div class="field"><span class="label">Job Ref:</span><span class="value">AB123</span></div>
    <div class="field"><span class="label">Hours:</span><span class="value">Part Time</span></div>
    """

    fields = labelled_fields(html)

    assert fields["job ref"] == "AB123"
    assert fields["hours"] == "Part Time"


def test_labels_are_normalised() -> None:
    """Trailing colons, case and stray whitespace vary between portals and mean nothing."""
    fields = labelled_fields("<dl><dt>  CONTRACT TYPE :  </dt><dd>Permanent</dd></dl>")

    assert fields["contract type"] == "Permanent"


def test_an_empty_value_is_dropped() -> None:
    """A label with nothing after it is not a fact; storing "" would look like an answer."""
    assert "salary" not in labelled_fields("<dl><dt>Salary</dt><dd>   </dd></dl>")


def test_a_label_with_no_value_cell_is_dropped() -> None:
    assert labelled_fields("<table><tr><th>Salary:</th></tr></table>") == {}


def test_empty_html_yields_nothing() -> None:
    assert labelled_fields("") == {}


def test_a_page_with_no_pairs_yields_nothing() -> None:
    assert labelled_fields("<p>Just some prose about the role.</p>") == {}


def test_a_very_long_value_is_not_treated_as_a_field() -> None:
    """A `dd` holding three paragraphs is the description, not a labelled fact."""
    fields = labelled_fields(f"<dl><dt>Salary</dt><dd>{'x' * 400}</dd></dl>")

    assert fields == {}


def test_the_first_occurrence_of_a_label_wins() -> None:
    """Portals repeat a label in a summary panel and again in the body.

    The summary comes first in the document and is the one stated deliberately.
    """
    html = "<dl><dt>Salary</dt><dd>Grade 7</dd><dt>Salary</dt><dd>Negotiable</dd></dl>"

    assert labelled_fields(html)["salary"] == "Grade 7"


def _vacancy(**overrides: object) -> RawVacancy:
    return RawVacancy(
        source_url="https://jobs.test.ac.uk/1",
        title="Technical Specialist",
        institution_slug="university-of-cambridge",
        **overrides,  # type: ignore[arg-type]
    )


def test_every_field_on_a_real_listing_is_mapped() -> None:
    """The listing that prompted this: all seven labelled facts reach the vacancy."""
    result = apply_labelled_fields(_vacancy(), labelled_fields(TABLE_HTML))

    assert result.location_raw == "Cambridge"
    assert result.salary_raw == "£35,608 to £46,049 per annum"
    assert result.hours_raw == "Full Time"
    assert result.contract_raw == "Fixed-Term/Contract"
    assert result.reference == "NM50033"
    assert result.posted_date == date(2026, 8, 7)
    assert result.closing_date == date(2026, 9, 6)


@pytest.mark.parametrize(
    ("label", "attribute"),
    [
        ("location", "location_raw"),
        ("salary", "salary_raw"),
        ("hours", "hours_raw"),
        ("contract type", "contract_raw"),
        ("contract", "contract_raw"),
        ("job ref", "reference"),
        ("reference", "reference"),
        ("vacancy reference", "reference"),
        ("department", "department"),
        ("faculty", "department"),
        ("grade", "grade_raw"),
        ("job type", "category"),
        ("category", "category"),
    ],
)
def test_label_synonyms(label: str, attribute: str) -> None:
    """Portals name the same fact half a dozen ways; the vacancy has one field for it."""
    result = apply_labelled_fields(_vacancy(), {label: "a value"})

    assert getattr(result, attribute) == "a value"


def test_an_unknown_label_is_kept_as_extra_rather_than_dropped() -> None:
    """Recorded but not interpreted - a fact nobody has mapped yet is still evidence."""
    result = apply_labelled_fields(_vacancy(), {"interview date": "12 October"})

    assert result.extra["interview date"] == "12 October"


def test_a_value_already_set_is_never_overwritten() -> None:
    """A listing page's own field beats one scraped from the detail page's furniture.

    The listing is where a platform states facts deliberately; the detail page is prose with a
    header, and reading it second means a worse value can never displace a better one.
    """
    result = apply_labelled_fields(_vacancy(salary_raw="£40,000"), {"salary": "Competitive"})

    assert result.salary_raw == "£40,000"


def test_an_unparseable_date_is_left_alone_rather_than_guessed() -> None:
    result = apply_labelled_fields(_vacancy(), {"closes": "when filled"})

    assert result.closing_date is None


def test_mapping_nothing_changes_nothing() -> None:
    original = _vacancy(salary_raw="£40,000")

    assert apply_labelled_fields(original, {}) == original
