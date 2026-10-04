import { Link } from "react-router-dom";

import { SiteFooterLinks } from "@/components/SiteFooter/SiteFooter";

const LAST_UPDATED = "3 October 2026";

const sectionClass = "mb-8";
const headingClass = "mb-2 text-heading-sm font-semibold";

export function PrivacyNotice() {
  return (
    <main id="main" className="mx-auto max-w-[68ch] px-4 py-10">
      <h1 className="mb-2 font-display text-heading-lg font-semibold text-text-primary">
        Privacy notice for UniJobs
      </h1>
      <p className="mb-8 text-body-sm text-text-secondary">Last updated {LAST_UPDATED}.</p>

      <section className={sectionClass}>
        <h2 className={headingClass}>Who is responsible for your data</h2>
        <p>
          The organisation that runs this copy of UniJobs is the data controller. It decides how
          your data is used and must answer your requests about it.
        </p>
      </section>

      <section className={sectionClass}>
        <h2 className={headingClass}>What we store and why</h2>
        <ul className="list-disc space-y-2 pl-6">
          <li>
            <strong>Your account:</strong> username, email address, name and role. We need these
            to sign you in and to send you account emails. Lawful basis: contract.
          </li>
          <li>
            <strong>Things you save:</strong> saved jobs, notes, applications, saved searches and
            your matching profile. They exist only because you created them. Lawful basis:
            contract.
          </li>
          <li>
            <strong>Your CV, if you upload one:</strong> the file and the text taken from it. We
            use it only to suggest skills for your matching profile. Nothing is saved to your
            profile until you confirm it. Lawful basis: consent. You can delete it at any time.
          </li>
          <li>
            <strong>Usage events:</strong> for example a search term and how many results it found.
            We use them to improve search. Lawful basis: legitimate interest.
          </li>
        </ul>
      </section>

      <section className={sectionClass}>
        <h2 className={headingClass}>What we do not do</h2>
        <ul className="list-disc space-y-2 pl-6">
          <li>We never send your data or your CV to an employer.</li>
          <li>We never apply for a job for you. Every Apply link opens the employer&apos;s site.</li>
          <li>We do not use advertising or tracking cookies, and we do not sell data.</li>
        </ul>
      </section>

      <section className={sectionClass}>
        <h2 className={headingClass}>How long we keep it</h2>
        <ul className="list-disc space-y-2 pl-6">
          <li>Your account and everything you saved: until you delete your account.</li>
          <li>Accounts that never confirmed their email address: 7 days.</li>
          <li>
            Usage events: 365 days. After that only daily totals remain, and they do not say who
            searched.
          </li>
          <li>
            Pages saved by the crawler from university sites: 90 days. They can contain the name
            of a contact person from a job advert.
          </li>
        </ul>
      </section>

      <section className={sectionClass}>
        <h2 className={headingClass}>Cookies and storage in your browser</h2>
        <p className="mb-3">
          We use two cookies. Both are strictly necessary for the service to work, so we do not
          ask for consent to set them.
        </p>
        <ul className="mb-3 list-disc space-y-2 pl-6">
          <li>
            <strong>sessionid</strong> keeps you signed in. Scripts cannot read it. It ends
            after 12 hours without use, or when you sign out.
          </li>
          <li>
            <strong>csrftoken</strong> is set when the app first loads. It protects your account
            against forged requests from other websites.
          </li>
        </ul>
        <p>
          Your browser also stores your colour theme and accessibility settings. We do not use
          tracking or advertising cookies.
        </p>
      </section>

      <section className={sectionClass}>
        <h2 className={headingClass}>Your rights</h2>
        <p className="mb-3">You can:</p>
        <ul className="mb-3 list-disc space-y-2 pl-6">
          <li>
            download a copy of all your data, from{" "}
            <Link to="/profile" className="text-brand underline underline-offset-2 hover:decoration-2">
              Account settings
            </Link>
          </li>
          <li>correct your details, from the same page</li>
          <li>delete your account, which also deletes everything you saved and any CV</li>
          <li>object to how we use your data, or ask us to limit it</li>
        </ul>
        <p>
          If you are not happy with our answer, you can complain to the Information
          Commissioner&apos;s Office (ICO) at{" "}
          <a href="https://ico.org.uk/make-a-complaint/" className="text-brand underline underline-offset-2 hover:decoration-2">
            ico.org.uk/make-a-complaint
          </a>
          .
        </p>
      </section>

      <SiteFooterLinks className="border-t border-border-subtle pt-4 text-body-sm text-text-secondary" />
    </main>
  );
}
