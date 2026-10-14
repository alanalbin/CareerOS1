import { useState, useEffect } from "react";
import { Link, useLocation } from "wouter";
import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Download,
  Sparkles,
  ChevronLeft,
  Loader2,
  FileCheck2,
  CheckCircle2,
  LayoutTemplate,
  Award,
  BookOpen,
  Briefcase,
  Github,
  Linkedin,
  RefreshCw,
} from "lucide-react";

type TemplateType = "Modern" | "Minimal" | "Technical" | "Professional" | "Student";

export default function ResumeBuilder() {
  const [, setLocation] = useLocation();
  const { isAuthenticated, user, loading: authLoading } = useAuth({
    redirectOnUnauthenticated: true,
    redirectPath: "/login/student",
  });

  const [template, setTemplate] = useState<TemplateType>("Modern");
  const [selectedCertIds, setSelectedCertIds] = useState<number[]>([]);
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  // Resume content state
  const [resumeData, setResumeData] = useState<any>(null);
  const [summary, setSummary] = useState("");
  const [targetRole, setTargetRole] = useState("");

  const resumeDataQuery = trpc.resume.data.useQuery(undefined, {
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (resumeDataQuery.data?.resumeData) {
      const data = resumeDataQuery.data.resumeData;
      setResumeData(data);
      setTargetRole(data.targetRole || "Software Engineer");
      setSummary(data.summary || `Dedicated ${data.targetRole || "Software Engineer"} with verified technical evidence, open source contributions, and strong academic foundations.`);
      if (data.certifications && data.certifications.length > 0) {
        setSelectedCertIds(data.certifications.map((c: any) => c.id));
      }
    }
  }, [resumeDataQuery.data]);

  const toggleCertSelection = (id: number) => {
    setSelectedCertIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleAiPolish = async () => {
    setIsGeneratingAi(true);
    try {
      const token = localStorage.getItem("careeros_token");
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/resume/generate", {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify({
          selectedCertificateIds: selectedCertIds,
          template,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "AI analysis is currently unavailable.");
      }

      const result = await res.json();
      if (result.aiData) {
        if (result.aiData.professionalSummary) {
          setSummary(result.aiData.professionalSummary);
        }
        toast.success("Resume content polished with Qwen3 AI!");
      } else if (result.resumeMarkdown) {
        toast.success("Resume sections formatted and organized.");
      }
    } catch (err: any) {
      toast.error(err.message || "AI analysis is currently unavailable.");
    } finally {
      setIsGeneratingAi(false);
    }
  };

  const handleDownloadPdf = async () => {
    setIsDownloadingPdf(true);
    try {
      const token = localStorage.getItem("careeros_token");
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const payload = {
        selectedCertificateIds: selectedCertIds,
        template,
        customData: {
          ...resumeData,
          summary,
          targetRole,
        },
      };

      const res = await fetch("/api/resume/pdf", {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Failed to generate PDF document.");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${user?.firstName || "Student"}_${user?.lastName || "Resume"}_Resume.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success("Professional PDF resume downloaded successfully!");
    } catch (err: any) {
      toast.error(err.message || "Failed to download PDF.");
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  if (authLoading || resumeDataQuery.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f7f8f5]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-[#135f52]" />
          <p className="text-xs font-semibold text-[#576b63]">Loading career records & artifacts...</p>
        </div>
      </div>
    );
  }

  const certs = resumeData?.certifications || [];
  const education = resumeData?.education || [];
  const skills = resumeData?.skills || [];
  const projects = resumeData?.projects || [];
  const experience = (resumeData?.experience || []).concat(resumeData?.internships || []);
  const github = resumeData?.github || {};
  const linkedin = resumeData?.linkedin || {};

  return (
    <div className="min-h-screen bg-[#f7f8f5] text-[#14221f]">
      {/* Top Navbar */}
      <header className="border-b border-[#dfe8e2] bg-white sticky top-0 z-20 px-6 py-3.5 shadow-xs">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/student" className="flex items-center gap-2 text-xs font-semibold text-[#62776e] hover:text-[#135f52] transition">
              <ChevronLeft size={16} /> Back to Student Workspace
            </Link>
            <span className="text-[#cbdad3]">|</span>
            <div className="flex items-center gap-2">
              <img src="/logo.svg" alt="Career OS" className="h-6 w-auto object-contain" />
              <span className="font-display text-sm font-bold tracking-tight text-[#14221f]">
                AI Resume Builder
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              onClick={handleAiPolish}
              disabled={isGeneratingAi}
              variant="outline"
              className="border-[#cbdad3] text-xs font-semibold text-[#135f52] hover:bg-[#eef7f3]"
            >
              {isGeneratingAi ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> Polishing with Qwen3...
                </>
              ) : (
                <>
                  <Sparkles className="mr-1.5 h-3.5 w-3.5 text-[#135f52]" /> AI Polish & Optimize
                </>
              )}
            </Button>
            <Button
              onClick={handleDownloadPdf}
              disabled={isDownloadingPdf}
              className="bg-[#135f52] hover:bg-[#0d5146] text-white text-xs font-semibold px-4 shadow-sm"
            >
              {isDownloadingPdf ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> Generating PDF...
                </>
              ) : (
                <>
                  <Download className="mr-1.5 h-3.5 w-3.5" /> Download PDF
                </>
              )}
            </Button>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <main className="max-w-7xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Configuration & Controls (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Template Selector */}
          <div className="bg-white rounded-xl border border-[#dce7e1] p-5 shadow-xs">
            <div className="flex items-center gap-2 mb-3">
              <LayoutTemplate size={16} className="text-[#135f52]" />
              <h2 className="font-display text-sm font-bold">Resume Template</h2>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {(["Modern", "Minimal", "Technical", "Professional", "Student"] as TemplateType[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTemplate(t)}
                  className={`py-2 px-3 text-xs font-semibold rounded-lg border text-center transition ${
                    template === t
                      ? "border-[#135f52] bg-[#eef7f3] text-[#135f52] shadow-xs"
                      : "border-[#e0ebe5] bg-white text-[#556961] hover:border-[#cbdad3]"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Target Role & Profile Summary */}
          <div className="bg-white rounded-xl border border-[#dce7e1] p-5 shadow-xs space-y-4">
            <div>
              <Label className="text-xs font-semibold text-[#3a5248]">Target Position</Label>
              <Input
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                className="mt-1 text-xs border-[#cbdad3]"
                placeholder="e.g. Full-Stack Software Engineer"
              />
            </div>
            <div>
              <div className="flex justify-between items-center mb-1">
                <Label className="text-xs font-semibold text-[#3a5248]">Professional Summary</Label>
                <button
                  onClick={handleAiPolish}
                  className="text-[11px] font-semibold text-[#135f52] flex items-center gap-1 hover:underline"
                >
                  <Sparkles size={11} /> AI Rephrase
                </button>
              </div>
              <Textarea
                rows={4}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                className="text-xs border-[#cbdad3] leading-relaxed"
                placeholder="Brief professional profile summary..."
              />
            </div>
          </div>

          {/* Certificate Selection */}
          <div className="bg-white rounded-xl border border-[#dce7e1] p-5 shadow-xs">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Award size={16} className="text-[#135f52]" />
                <h2 className="font-display text-sm font-bold">Include Certifications</h2>
              </div>
              <span className="text-[11px] text-[#71857c] font-semibold">
                {selectedCertIds.length} of {certs.length} selected
              </span>
            </div>

            {certs.length > 0 ? (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {certs.map((c: any) => {
                  const isChecked = selectedCertIds.includes(c.id);
                  return (
                    <div
                      key={c.id}
                      onClick={() => toggleCertSelection(c.id)}
                      className={`flex items-start gap-3 p-2.5 rounded-lg border cursor-pointer transition ${
                        isChecked
                          ? "border-[#135f52] bg-[#f2f8f5]"
                          : "border-[#e0ebe5] bg-white opacity-70 hover:opacity-100"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {}}
                        className="mt-0.5 rounded text-[#135f52] focus:ring-[#135f52]"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-[#14221f] truncate">{c.title}</p>
                        <p className="text-[11px] text-[#697c74]">
                          {c.issuer} {c.issue_date ? `· ${c.issue_date}` : ""}
                        </p>
                      </div>
                      {c.verified && (
                        <span className="text-[10px] font-bold text-[#135f52] bg-[#e1f0e9] px-2 py-0.5 rounded">
                          OCR Verified
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-[#71857c] italic py-3 text-center">
                No certificates uploaded yet. Upload certificates in your Evidence Library.
              </p>
            )}
          </div>
        </div>

        {/* Right Column: Live A4 Resume Preview (7 cols) */}
        <div className="lg:col-span-7">
          <div className="bg-white rounded-2xl border border-[#dce7e1] p-8 md:p-12 shadow-sm min-h-[750px] font-sans text-[#14221f]">
            {/* Header */}
            <div className="border-b border-[#e0ebe5] pb-5 mb-5">
              <h1 className="text-2xl font-bold font-display text-[#135f52] tracking-tight">
                {resumeData?.name || "Candidate Name"}
              </h1>
              <p className="text-xs font-bold text-[#445b52] mt-0.5 uppercase tracking-wide">
                {targetRole}
              </p>
              <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-[#62776e]">
                <span>{resumeData?.email}</span>
                {resumeData?.phone && <span>• {resumeData.phone}</span>}
                {github.username && (
                  <span>
                    • <a href={github.profileUrl} target="_blank" rel="noreferrer" className="text-[#135f52] underline">github.com/{github.username}</a>
                  </span>
                )}
                {linkedin.username && (
                  <span>
                    • <a href={linkedin.profileUrl} target="_blank" rel="noreferrer" className="text-[#135f52] underline">linkedin.com/in/{linkedin.username}</a>
                  </span>
                )}
                {resumeData?.collegeName && <span>• {resumeData.collegeName}</span>}
              </div>
            </div>

            {/* Summary */}
            {summary && (
              <div className="mb-5">
                <h3 className="text-xs font-bold text-[#135f52] uppercase tracking-wider mb-1.5">
                  Professional Summary
                </h3>
                <p className="text-xs leading-relaxed text-[#2c3d36]">{summary}</p>
              </div>
            )}

            {/* Education */}
            {education.length > 0 && (
              <div className="mb-5">
                <h3 className="text-xs font-bold text-[#135f52] uppercase tracking-wider mb-2">
                  Education
                </h3>
                <div className="space-y-2">
                  {education.map((edu: any, idx: number) => (
                    <div key={idx} className="text-xs">
                      <div className="flex justify-between font-semibold text-[#14221f]">
                        <span>{edu.degree} {edu.field_of_study ? `in ${edu.field_of_study}` : ""}</span>
                        <span className="text-[#62776e]">{edu.start_year || ""} – {edu.end_year || "Present"}</span>
                      </div>
                      <div className="flex justify-between text-[#556961]">
                        <span>{edu.institution}</span>
                        {edu.grade_cgpa && <span className="font-semibold text-[#135f52]">CGPA: {edu.grade_cgpa}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Technical Skills */}
            {skills.length > 0 && (
              <div className="mb-5">
                <h3 className="text-xs font-bold text-[#135f52] uppercase tracking-wider mb-1.5">
                  Technical Skills & Competencies
                </h3>
                <p className="text-xs text-[#2c3d36] leading-relaxed">
                  <span className="font-semibold text-[#14221f]">Verified Capabilities: </span>
                  {skills.join(", ")}
                </p>
              </div>
            )}

            {/* Projects */}
            {projects.length > 0 && (
              <div className="mb-5">
                <h3 className="text-xs font-bold text-[#135f52] uppercase tracking-wider mb-2">
                  Technical Projects
                </h3>
                <div className="space-y-2.5">
                  {projects.slice(0, 4).map((p: any, idx: number) => (
                    <div key={idx} className="text-xs">
                      <div className="flex justify-between font-semibold text-[#14221f]">
                        <span>{p.title}</span>
                        {p.technologies && <span className="font-normal italic text-[#62776e]">{p.technologies}</span>}
                      </div>
                      {p.description && (
                        <p className="text-[#3b4e47] mt-0.5 leading-relaxed">• {p.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Experience / Internships */}
            {experience.length > 0 && (
              <div className="mb-5">
                <h3 className="text-xs font-bold text-[#135f52] uppercase tracking-wider mb-2">
                  Experience & Internships
                </h3>
                <div className="space-y-2.5">
                  {experience.slice(0, 3).map((exp: any, idx: number) => (
                    <div key={idx} className="text-xs">
                      <div className="flex justify-between font-semibold text-[#14221f]">
                        <span>{exp.role}</span>
                        <span className="text-[#62776e]">{exp.period || exp.duration || ""}</span>
                      </div>
                      <p className="text-[#556961] font-medium">{exp.company}</p>
                      {exp.description && (
                        <p className="text-[#3b4e47] mt-0.5 leading-relaxed">• {exp.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Selected Certifications */}
            {selectedCertIds.length > 0 && (
              <div>
                <h3 className="text-xs font-bold text-[#135f52] uppercase tracking-wider mb-2">
                  Verified Certifications
                </h3>
                <div className="space-y-1.5">
                  {certs
                    .filter((c: any) => selectedCertIds.includes(c.id))
                    .map((c: any) => (
                      <div key={c.id} className="text-xs flex items-center justify-between text-[#2c3d36]">
                        <span>
                          • <span className="font-semibold">{c.title}</span> — {c.issuer}
                        </span>
                        <span className="text-[#72857e]">{c.issue_date || "Verified"}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
