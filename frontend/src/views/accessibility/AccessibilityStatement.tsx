import { SiteFooterLinks } from "@/components/SiteFooter/SiteFooter";

const PREPARED_DATE = "14 September 2026";
const REVIEWED_DATE = "3 October 2026";
const FEEDBACK_URL = "https://github.com/mjanzikhan7/unijobs/issues/new";

export function AccessibilityStatement() {
  return (
    <main id="main" className="mx-auto max-w-[68ch] px-4 py-10">
      <h1 className="mb-2 font-display text-heading-lg font-semibold text-text-primary">
        Accessibility statement for UniJobs
      </h1>
      <p className="mb-8 text-body-sm text-text-secondary">
        Prepared {PREPARED_DATE}. Last reviewed {REVIEWED_DATE}.
      </p>

      <section className="mb-8">
        <h2 className="mb-2 text-heading-sm font-semibold">Scope</h2>
        <p>
          This statement covers the UniJobs web application at this domain: job search, job
          detail, saved jobs, the application pipeline, institution pages, account settings and
          the operator screens (crawl console, sponsor review, manage jobs/institutions). It does
          not cover employers&apos; own job-advert pages, which UniJobs links to but does not
          control.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="mb-2 text-heading-sm font-semibold">What we support</h2>
        <p className="mb-3">
          UniJobs is built to work with a keyboard alone, with screen readers including NVDA,
          JAWS and VoiceOver, at up to 400% browser zoom, and with Windows High Contrast Mode.
        </p>
        <p>
          The accessibility button in the corner of the screen (or <kbd>Alt</kbd>+<kbd>0</kbd>)
          opens settings for text size, spacing, fonts, colour and contrast, motion, and reading
          the page aloud. Those settings are a preference layer, not a substitute for the points
          above: if a page is missing a label or a heading, that is a defect in the page, and the
          settings will not hide it.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="mb-2 text-heading-sm font-semibold">Conformance status</h2>
        <p>
          UniJobs is <strong>partially conformant</strong> with WCAG 2.2 level AA. &ldquo;Partially
          conformant&rdquo; means some parts of the content do not yet fully conform to the
          accessibility standard. We do not claim full conformance until an automated test suite
          (axe, Lighthouse, and a keyboard-only journey on every key route) passes with zero
          serious or critical violations, which it does not yet.
        </p>
        <p className="mt-3">
          This statement is written to meet the Public Sector Bodies (Websites and Mobile
          Applications) (No. 2) Accessibility Regulations 2018, which UK universities must follow.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="mb-2 text-heading-sm font-semibold">Known issues</h2>
        <ul className="list-disc space-y-2 pl-6">
          <li>
            Job detail and institution detail pages do not yet update the browser tab title or
            announce a specific page name on navigation — they announce as &ldquo;Page&rdquo;
            rather than the job or institution title (2.4.2, 4.1.3).
          </li>
          <li>
            While a colour filter (monochrome, soft or vivid colours, the colour-vision modes or
            invert) is switched on in the accessibility settings, the Apply bar on job detail pages
            on small screens scrolls with the page instead of staying fixed at the bottom.
          </li>
          <li>
            Reading aloud uses your browser&apos;s own voices, so the voices available differ
            between devices. Browsers without the CSS Custom Highlight API read the text without
            highlighting it.
          </li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="mb-2 text-heading-sm font-semibold">Feedback and contact</h2>
        <p>
          If you find a problem that is not listed here, or you need information in a different
          format, please{" "}
          <a href={FEEDBACK_URL} className="text-brand underline underline-offset-2 hover:decoration-2">
            tell us about it
          </a>
          . We aim to reply within 5 working days.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="mb-2 text-heading-sm font-semibold">Enforcement procedure</h2>
        <p>
          The Equality and Human Rights Commission (EHRC) enforces the accessibility regulations.
          If you are not happy with how we respond, contact the{" "}
          <a href="https://www.equalityadvisoryservice.com/" className="text-brand underline underline-offset-2 hover:decoration-2">
            Equality Advisory and Support Service (EASS)
          </a>
          . If you are in Northern Ireland, contact the{" "}
          <a href="https://www.equalityni.org/" className="text-brand underline underline-offset-2 hover:decoration-2">
            Equality Commission for Northern Ireland (ECNI)
          </a>{" "}
          instead.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="mb-2 text-heading-sm font-semibold">Disproportionate burden</h2>
        <p>We do not claim disproportionate burden for any part of this service.</p>
      </section>

      <section className="mb-8">
        <h2 className="mb-2 text-heading-sm font-semibold">Preparation and testing</h2>
        <p>
          This statement was prepared on {PREPARED_DATE} from a manual review against WCAG 2.2 AA,
          plus automated axe-core checks: in Storybook for each component, and in the
          end-to-end tests for the main screens and the accessibility settings. It was last reviewed on {REVIEWED_DATE}.
        </p>
      </section>

      <SiteFooterLinks className="border-t border-border-subtle pt-4 text-body-sm text-text-secondary" />
    </main>
  );
}
