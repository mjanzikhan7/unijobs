import { Suspense, lazy, useState } from "react";
import { Provider } from "react-redux";
import { ThemeProvider } from "@mui/material/styles";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { A11yProvider, A11yToolbar } from "@unijobs/a11y/react";

import { Spinner } from "@/components/Feedback";
import { AppShell } from "@/components/AppShell/AppShell";
import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { createAppStore } from "@/store/store";
import { AuthProvider, useAuth } from "@/viewmodels/auth";
import { muiTheme } from "@/styles/muiTheme";
import { ForgotPassword } from "@/views/auth/ForgotPassword";
import { Login } from "@/views/auth/Login";
import { Register } from "@/views/auth/Register";
import { ResetPassword } from "@/views/auth/ResetPassword";
import { VerifyEmail } from "@/views/auth/VerifyEmail";
import { VerifyEmailChange } from "@/views/auth/VerifyEmailChange";
import { InstitutionDetail } from "@/views/institutions/InstitutionDetail";
import { InstitutionList } from "@/views/institutions/InstitutionList";
import { JobDetail } from "@/views/jobs/JobDetail";
import { JobList } from "@/views/jobs/JobList";
import { PipelineBoard } from "@/views/pipeline/PipelineBoard";
import { AccountSettings } from "@/views/profile/AccountSettings";
import { CandidateProfile } from "@/views/profile/CandidateProfile";
import { SavedJobs } from "@/views/saved/SavedJobs";

const CrawlConsole = lazy(() =>
  import("@/views/crawl/CrawlConsole").then((m) => ({ default: m.CrawlConsole })),
);
const RunDetail = lazy(() =>
  import("@/views/crawl/RunDetail").then((m) => ({ default: m.RunDetail })),
);
const ReviewQueue = lazy(() =>
  import("@/views/institutions/ReviewQueue").then((m) => ({ default: m.ReviewQueue })),
);
const RulesetSettings = lazy(() =>
  import("@/views/settings/RulesetSettings").then((m) => ({ default: m.RulesetSettings })),
);
const UserAdmin = lazy(() =>
  import("@/views/admin/UserAdmin").then((m) => ({ default: m.UserAdmin })),
);
const JobAdmin = lazy(() =>
  import("@/views/admin/JobAdmin").then((m) => ({ default: m.JobAdmin })),
);
const InstitutionAdmin = lazy(() =>
  import("@/views/admin/InstitutionAdmin").then((m) => ({ default: m.InstitutionAdmin })),
);
const AddInstitution = lazy(() =>
  import("@/views/admin/AddInstitution").then((m) => ({ default: m.AddInstitution })),
);
const CandidateInsights = lazy(() =>
  import("@/views/admin/CandidateInsights").then((m) => ({ default: m.CandidateInsights })),
);
const InstitutionInsights = lazy(() =>
  import("@/views/admin/InstitutionInsights").then((m) => ({ default: m.InstitutionInsights })),
);
const AddJob = lazy(() =>
  import("@/views/admin/AddJob").then((m) => ({ default: m.AddJob })),
);
const EditJob = lazy(() =>
  import("@/views/admin/EditJob").then((m) => ({ default: m.EditJob })),
);
const MyInstitution = lazy(() =>
  import("@/views/recruiter/MyInstitution").then((m) => ({ default: m.MyInstitution })),
);
const PrivacyNotice = lazy(() =>
  import("@/views/privacy/PrivacyNotice").then((m) => ({ default: m.PrivacyNotice })),
);
const AccessibilityStatement = lazy(() =>
  import("@/views/accessibility/AccessibilityStatement").then((m) => ({
    default: m.AccessibilityStatement,
  })),
);

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <Spinner label="Loading" />;
  if (!user) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <>{children}</>;
}

function RequireStaff({ children }: { children: React.ReactNode }) {
  const { isStaff } = useAuth();
  if (!isStaff) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function RequireJobManager({ children }: { children: React.ReactNode }) {
  const { isStaff, role } = useAuth();
  if (!isStaff && role !== "RECRUITER") return <Navigate to="/" replace />;
  return <>{children}</>;
}

function RequireRecruiter({ children }: { children: React.ReactNode }) {
  const { role } = useAuth();
  if (role !== "RECRUITER") return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function App() {
  const [store] = useState(createAppStore);

  return (
    <A11yProvider>
      <Provider store={store}>
        <ThemeProvider theme={muiTheme} defaultMode="system" modeStorageKey="theme" noSsr>
          <BrowserRouter>
            <AuthProvider>
              <Suspense fallback={<Spinner label="Loading" />}>
                <Routes>
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  <Route path="/verify-email/:token" element={<VerifyEmail />} />
                  <Route path="/verify-email-change/:token" element={<VerifyEmailChange />} />
                  <Route path="/forgot-password" element={<ForgotPassword />} />
                  <Route path="/reset-password/:uid/:token" element={<ResetPassword />} />
                  <Route path="/accessibility" element={<AccessibilityStatement />} />
                  <Route path="/privacy" element={<PrivacyNotice />} />

                  <Route
                    element={
                      <RequireAuth>
                        <AppShell />
                      </RequireAuth>
                    }
                  >
                    <Route index element={<JobList />} />
                    <Route path="jobs/:id" element={<JobDetail />} />
                    <Route path="institutions" element={<InstitutionList />} />
                    <Route path="institutions/:slug" element={<InstitutionDetail />} />
                    <Route path="saved" element={<SavedJobs />} />
                    <Route path="pipeline" element={<PipelineBoard />} />
                    <Route path="profile" element={<AccountSettings />} />
                    <Route path="profile/cv" element={<CandidateProfile />} />

                    <Route
                      path="admin/crawl"
                      element={
                        <RequireStaff>
                          <CrawlConsole />
                        </RequireStaff>
                      }
                    />
                    <Route
                      path="admin/crawl/:id"
                      element={
                        <RequireStaff>
                          <RunDetail />
                        </RequireStaff>
                      }
                    />
                    <Route
                      path="admin/review"
                      element={
                        <RequireStaff>
                          <ReviewQueue />
                        </RequireStaff>
                      }
                    />
                    <Route
                      path="admin/jobs"
                      element={
                        <RequireJobManager>
                          <JobAdmin />
                        </RequireJobManager>
                      }
                    />
                    <Route
                      path="admin/jobs/new"
                      element={
                        <RequireJobManager>
                          <AddJob />
                        </RequireJobManager>
                      }
                    />
                    <Route
                      path="admin/jobs/:id/edit"
                      element={
                        <RequireJobManager>
                          <EditJob />
                        </RequireJobManager>
                      }
                    />
                    <Route
                      path="recruiter/institution"
                      element={
                        <RequireRecruiter>
                          <MyInstitution />
                        </RequireRecruiter>
                      }
                    />
                    <Route
                      path="admin/institutions"
                      element={
                        <RequireStaff>
                          <InstitutionAdmin />
                        </RequireStaff>
                      }
                    />
                    <Route
                      path="admin/institutions/new"
                      element={
                        <RequireStaff>
                          <AddInstitution />
                        </RequireStaff>
                      }
                    />
                    <Route
                      path="admin/insights"
                      element={
                        <RequireStaff>
                          <CandidateInsights />
                        </RequireStaff>
                      }
                    />
                    <Route
                      path="admin/insights/institutions"
                      element={
                        <RequireStaff>
                          <InstitutionInsights />
                        </RequireStaff>
                      }
                    />
                    <Route
                      path="admin/users"
                      element={
                        <RequireStaff>
                          <UserAdmin />
                        </RequireStaff>
                      }
                    />
                    <Route
                      path="admin/thresholds"
                      element={
                        <RequireStaff>
                          <RulesetSettings />
                        </RequireStaff>
                      }
                    />

                    <Route path="*" element={<NotFound />} />
                  </Route>
                </Routes>
              </Suspense>
            </AuthProvider>
          </BrowserRouter>
        </ThemeProvider>
      </Provider>
      <A11yToolbar />
    </A11yProvider>
  );
}

function NotFound() {
  return (
    <EmptyPanel
      title="Not found"
      body="That page does not exist. It may have moved, or the link may be wrong."
      action={
        <Link to="/" className="text-brand underline underline-offset-2 hover:decoration-2">
          Back to the job list
        </Link>
      }
    />
  );
}
